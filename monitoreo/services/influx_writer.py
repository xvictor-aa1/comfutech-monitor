# monitoreo/services/influx_writer.py
"""
Escritura en InfluxDB 2.x.

Características:
  - Cliente compartido (se recrea si cambia la configuración).
  - Escritura tolerante a fallos: NUNCA propaga excepciones a los
    pollers (se loguea a DEBUG y se devuelve False).
  - Detección de config incompleta (URL o token vacíos).
  - Cierre automático con atexit.
"""
import atexit
import logging
import threading
from typing import Optional

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from core.runtime_config import get_influx_config

log = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN
# ============================================================
INFLUX_TIMEOUT_MS = 5000    # timeout por escritura
POOL_MAXSIZE = 10           # pool de conexiones


# ============================================================
# CLIENTE COMPARTIDO
# ============================================================
_client: Optional[InfluxDBClient] = None
_write_api = None
_client_lock = threading.Lock()
_cached_url: Optional[str] = None
_cached_token: Optional[str] = None


def _get_write_api():
    """
    Devuelve el write_api compartido, recreándolo si la config cambió.

    Returns:
        write_api listo para escribir, o None si la config está incompleta.
    """
    global _client, _write_api, _cached_url, _cached_token

    cfg = get_influx_config()
    if not cfg["url"] or not cfg["token"]:
        return None

    with _client_lock:
        # ¿Cambió la config?
        needs_reset = (
            _write_api is None
            or _cached_url != cfg["url"]
            or _cached_token != cfg["token"]
        )
        if needs_reset:
            if _client:
                try:
                    _client.close()
                except Exception:
                    pass
                _client = None
                _write_api = None

            try:
                _client = InfluxDBClient(
                    url=cfg["url"],
                    token=cfg["token"],
                    org=cfg["org"],
                    timeout=INFLUX_TIMEOUT_MS,
                    connection_pool_maxsize=POOL_MAXSIZE,
                )
                _write_api = _client.write_api(write_options=SYNCHRONOUS)
                _cached_url = cfg["url"]
                _cached_token = cfg["token"]
            except Exception as e:
                log.error("Error creando cliente InfluxDB: %s", e)
                _client = None
                _write_api = None
                return None

        return _write_api


def close():
    """
    Cierra el cliente InfluxDB y limpia la caché.

    Se llama con atexit y desde `reset()` cuando cambia la config.
    """
    global _client, _write_api, _cached_url, _cached_token
    with _client_lock:
        if _client:
            try:
                _client.close()
            except Exception:
                pass
            _client = None
            _write_api = None
            _cached_url = None
            _cached_token = None


def reset():
    """Fuerza la recarga de config en el próximo write."""
    close()


# ============================================================
# ESCRITURA GENÉRICA
# ============================================================
def _write_point(point: Point) -> bool:
    """
    Escribe un punto. NUNCA propaga excepciones.

    Args:
        point: instancia de Point configurada.

    Returns:
        bool: True si se escribió correctamente.
    """
    api = _get_write_api()
    if api is None:
        return False

    try:
        cfg = get_influx_config()
        api.write(
            bucket=cfg["bucket"],
            org=cfg["org"],
            record=point,
        )
        return True
    except Exception as e:
        # Nivel DEBUG para evitar spam; los fallos son recuperables
        log.debug("InfluxDB write falló: %s", e)
        return False


# ============================================================
# ESCRITORES ESPECÍFICOS
# ============================================================
def write_traffic(
    device_name: str,
    ip: str,
    if_index: int,
    if_name: Optional[str],
    role: Optional[str],
    capacity_bps: Optional[int],
    in_bps: Optional[float],
    out_bps: Optional[float],
    utilization: Optional[float],
    rx_octets: Optional[int],
    tx_octets: Optional[int],
    timestamp,
) -> bool:
    """
    Escribe un punto del measurement `traffic`.

    Args:
        device_name, ip, if_index, if_name, role: tags.
        capacity_bps, in_bps, out_bps, utilization: fields.
        rx_octets, tx_octets: contadores absolutos del equipo.
        timestamp: datetime UTC naive.

    Returns:
        bool: True si se escribió.
    """
    point = (
        Point("traffic")
        .tag("device", device_name or "")
        .tag("ip", ip or "")
        .tag("interface", if_name or f"if{if_index}")
        .tag("role", role or "access")
        .field("in_bps", float(in_bps) if in_bps is not None else 0.0)
        .field("out_bps", float(out_bps) if out_bps is not None else 0.0)
        .field("utilization_pct", float(utilization) if utilization is not None else 0.0)
        .field("capacity_bps", int(capacity_bps) if capacity_bps else 0)
        .field("rx_octets", int(rx_octets) if rx_octets is not None else 0)
        .field("tx_octets", int(tx_octets) if tx_octets is not None else 0)
        .time(timestamp)
    )
    return _write_point(point)


def write_health(
    device_name: str,
    ip: str,
    role: Optional[str],
    vendor: Optional[str],
    metrics: dict,
    timestamp,
) -> bool:
    """
    Escribe un punto del measurement `health`.

    Solo se escriben los fields que existan en `metrics` (cpu_pct,
    mem_pct, temp_c, uptime). Si ninguno está presente, no se escribe.

    Args:
        device_name, ip, role, vendor: tags.
        metrics: dict con los valores disponibles.
        timestamp: datetime UTC naive.

    Returns:
        bool: True si se escribió algo.
    """
    point = (
        Point("health")
        .tag("device", device_name or "")
        .tag("ip", ip or "")
        .tag("role", role or "core")
        .tag("vendor", vendor or "generic")
    )
    wrote = False
    for key in ("cpu_pct", "mem_pct", "temp_c", "uptime"):
        v = metrics.get(key)
        if v is not None:
            point = point.field(key, float(v))
            wrote = True

    if not wrote:
        return False
    return _write_point(point.time(timestamp))


def write_icmp(
    device_name: str,
    ip: str,
    role: Optional[str],
    alive: bool,
    avg_rtt: Optional[float],
    loss: float,
    timestamp,
) -> bool:
    """
    Escribe un punto del measurement `icmp`.

    Args:
        device_name, ip, role: tags.
        alive: si respondió al ping.
        avg_rtt: latencia media (ms) o None.
        loss: porcentaje de pérdida.
        timestamp: datetime UTC naive.

    Returns:
        bool: True si se escribió.
    """
    point = (
        Point("icmp")
        .tag("device", device_name or "")
        .tag("ip", ip or "")
        .tag("role", role or "access")
        .field("is_alive", 1 if alive else 0)
        .field("latency_ms", float(avg_rtt) if avg_rtt is not None else 0.0)
        .field("packet_loss_pct", float(loss))
        .time(timestamp)
    )
    return _write_point(point)


def write_tcp(
    device_name: str,
    ip: str,
    role: Optional[str],
    port: int,
    is_open: bool,
    timestamp,
) -> bool:
    """
    Escribe un punto del measurement `tcp`.

    Args:
        device_name, ip, role, port: tags.
        is_open: True si el puerto estaba abierto.
        timestamp: datetime UTC naive.

    Returns:
        bool: True si se escribió.
    """
    point = (
        Point("tcp")
        .tag("device", device_name or "")
        .tag("ip", ip or "")
        .tag("role", role or "access")
        .tag("port", str(port))
        .field("is_open", 1 if is_open else 0)
        .time(timestamp)
    )
    return _write_point(point)


# ============================================================
# CIERRE AUTOMÁTICO AL SALIR
# ============================================================
# Se registra para que el cliente se cierre ANTES de que Python
# destruya los módulos. Evita el TypeError del __del__ del cliente
# de influxdb_client al terminar el intérprete.
atexit.register(close)