# monitoreo/services/influx_reader.py
"""
Lectura de las últimas métricas desde InfluxDB.

Optimizaciones clave:
  - Un ÚNICO cliente InfluxDB compartido (no uno por consulta).
  - Caché en memoria (TTL configurable) para el snapshot completo.
  - Errores silenciosos: si InfluxDB falla, devuelve dicts vacíos
    en lugar de lanzar excepción.
  - Timeout holgado (10s) por si InfluxDB está bajo carga.

Con esto, aunque haya 10 clientes remotos consultando al mismo tiempo,
solo se hacen 4 queries reales por cada TTL al servidor InfluxDB.
"""
import atexit
import logging
import threading
import time
from typing import Optional

from influxdb_client import InfluxDBClient

from core.runtime_config import get_influx_config

log = logging.getLogger(__name__)

# Rango de tiempo hacia atrás para "última métrica"
LOOKBACK_RANGE = "-1h"

# TTL de la caché del snapshot (segundos)
CACHE_SECONDS = 5

# Timeout de cada consulta a InfluxDB
INFLUX_TIMEOUT_MS = 10000

# Pool de conexiones
POOL_MAXSIZE = 20


# ============================================================
# ESTADO GLOBAL
# ============================================================
_client: Optional[InfluxDBClient] = None
_client_lock = threading.Lock()
_cached_url: Optional[str] = None
_cached_token: Optional[str] = None

_snapshot_cache: dict = {}
_snapshot_cache_time: float = 0.0
_snapshot_lock = threading.Lock()


# ============================================================
# GESTIÓN DEL CLIENTE
# ============================================================
def _get_client() -> Optional[InfluxDBClient]:
    """
    Devuelve el cliente InfluxDB compartido, recreándolo si cambió
    la configuración (URL o token).

    Returns:
        InfluxDBClient o None si la config está incompleta.
    """
    global _client, _cached_url, _cached_token

    cfg = get_influx_config()
    if not cfg["url"] or not cfg["token"]:
        return None

    with _client_lock:
        # Si cambió la config, cerrar el cliente actual
        if _client and (_cached_url != cfg["url"] or _cached_token != cfg["token"]):
            try:
                _client.close()
            except Exception:
                pass
            _client = None

        # Crear si no existe
        if _client is None:
            _client = InfluxDBClient(
                url=cfg["url"],
                token=cfg["token"],
                org=cfg["org"],
                timeout=INFLUX_TIMEOUT_MS,
                connection_pool_maxsize=POOL_MAXSIZE,
            )
            _cached_url = cfg["url"]
            _cached_token = cfg["token"]

        return _client


def close():
    """
    Cierra el cliente InfluxDB compartido.

    Se llama al salir del proceso (atexit) y cuando la config cambia.
    """
    global _client, _cached_url, _cached_token
    with _client_lock:
        if _client:
            try:
                _client.close()
            except Exception:
                pass
            _client = None
            _cached_url = None
            _cached_token = None


def invalidate_cache():
    """
    Invalida la caché del snapshot.

    Se llama cuando el usuario guarda la configuración de InfluxDB
    para forzar la próxima consulta a traer datos frescos.
    """
    global _snapshot_cache, _snapshot_cache_time
    with _snapshot_lock:
        _snapshot_cache = {}
        _snapshot_cache_time = 0.0
    log.info("Caché de InfluxDB invalidada.")


# ============================================================
# QUERIES POR MEASUREMENT
# ============================================================
def _query_last_icmp(client, bucket: str) -> dict:
    """
    Últimos valores ICMP por dispositivo.

    Returns:
        dict: {device_name: {alive, rtt, loss, ts}}
    """
    try:
        qapi = client.query_api()
        flux = f'''
        from(bucket: "{bucket}")
          |> range(start: {LOOKBACK_RANGE})
          |> filter(fn: (r) => r._measurement == "icmp")
          |> filter(fn: (r) => r._field == "is_alive"
                              or r._field == "latency_ms"
                              or r._field == "packet_loss_pct")
          |> last()
        '''
        records = []
        for table in qapi.query(flux):
            records.extend(table.records)

        result = {}
        for r in records:
            device = r.values.get("device")
            field = r.get_field()
            value = r.get_value()
            ts = r.get_time()

            if device not in result:
                result[device] = {"ts": ts}
            result[device][field] = value
            if ts and (not result[device].get("ts") or ts > result[device]["ts"]):
                result[device]["ts"] = ts

        for d in result:
            r = result[d]
            r["alive"] = bool(r.get("is_alive", 0))
            r["rtt"] = r.get("latency_ms")
            r["loss"] = r.get("packet_loss_pct")
            r.pop("is_alive", None)
            r.pop("latency_ms", None)
            r.pop("packet_loss_pct", None)

        return result
    except Exception as e:
        log.warning("Error consultando ICMP en InfluxDB: %s", e)
        return {}


def _query_last_traffic(client, bucket: str) -> dict:
    """
    Últimos valores de tráfico por dispositivo/interfaz.

    Returns:
        dict: {device_name: [{interface, in_bps, out_bps, utilization_pct,
                              capacity_bps, ts}, ...]}
    """
    try:
        qapi = client.query_api()
        flux = f'''
        from(bucket: "{bucket}")
          |> range(start: {LOOKBACK_RANGE})
          |> filter(fn: (r) => r._measurement == "traffic")
          |> filter(fn: (r) => r._field == "in_bps"
                              or r._field == "out_bps"
                              or r._field == "utilization_pct"
                              or r._field == "capacity_bps")
          |> last()
        '''
        records = []
        for table in qapi.query(flux):
            records.extend(table.records)

        result = {}
        for r in records:
            device = r.values.get("device")
            interface = r.values.get("interface")
            field = r.get_field()
            value = r.get_value()
            ts = r.get_time()

            if device not in result:
                result[device] = {}
            if interface not in result[device]:
                result[device][interface] = {"interface": interface, "ts": ts}
            result[device][interface][field] = value
            if ts and (not result[device][interface].get("ts")
                       or ts > result[device][interface]["ts"]):
                result[device][interface]["ts"] = ts

        for device in result:
            result[device] = list(result[device].values())

        return result
    except Exception as e:
        log.warning("Error consultando traffic en InfluxDB: %s", e)
        return {}


def _query_last_health(client, bucket: str) -> dict:
    """
    Últimos valores de chasis por dispositivo.

    Returns:
        dict: {device_name: {cpu, mem, temp, uptime, ts}}
    """
    try:
        qapi = client.query_api()
        flux = f'''
        from(bucket: "{bucket}")
          |> range(start: {LOOKBACK_RANGE})
          |> filter(fn: (r) => r._measurement == "health")
          |> filter(fn: (r) => r._field == "cpu_pct"
                              or r._field == "mem_pct"
                              or r._field == "temp_c"
                              or r._field == "uptime")
          |> last()
        '''
        records = []
        for table in qapi.query(flux):
            records.extend(table.records)

        result = {}
        for r in records:
            device = r.values.get("device")
            field = r.get_field()
            value = r.get_value()
            ts = r.get_time()

            if device not in result:
                result[device] = {"ts": ts}
            result[device][field] = value
            if ts and (not result[device].get("ts") or ts > result[device]["ts"]):
                result[device]["ts"] = ts

        for d in result:
            r = result[d]
            r["cpu"] = r.pop("cpu_pct", None)
            r["mem"] = r.pop("mem_pct", None)
            r["temp"] = r.pop("temp_c", None)
            r["uptime"] = r.pop("uptime", None)

        return result
    except Exception as e:
        log.warning("Error consultando health en InfluxDB: %s", e)
        return {}


def _query_last_tcp(client, bucket: str) -> dict:
    """
    Últimos valores de puertos TCP por dispositivo.

    Returns:
        dict: {device_name: [{port, is_open, ts}, ...]}
    """
    try:
        qapi = client.query_api()
        flux = f'''
        from(bucket: "{bucket}")
          |> range(start: {LOOKBACK_RANGE})
          |> filter(fn: (r) => r._measurement == "tcp")
          |> filter(fn: (r) => r._field == "is_open")
          |> last()
        '''
        records = []
        for table in qapi.query(flux):
            records.extend(table.records)

        result = {}
        for r in records:
            device = r.values.get("device")
            port = r.values.get("port")
            value = r.get_value()
            ts = r.get_time()

            if device not in result:
                result[device] = []
            result[device].append({
                "port": port,
                "is_open": bool(value),
                "ts": ts,
            })

        return result
    except Exception as e:
        log.warning("Error consultando tcp en InfluxDB: %s", e)
        return {}


# ============================================================
# SNAPSHOT CON CACHÉ
# ============================================================
def get_live_snapshot() -> dict:
    """
    Devuelve todas las últimas métricas consolidadas.

    Usa caché de CACHE_SECONDS segundos para evitar saturar InfluxDB
    cuando hay múltiples clientes remotos haciendo polling.

    Si InfluxDB falla o no está configurado, devuelve dicts vacíos.

    Returns:
        dict: {"icmp": {}, "traffic": {}, "health": {}, "tcp": {}}
    """
    global _snapshot_cache, _snapshot_cache_time

    # ¿Caché válida?
    now = time.time()
    with _snapshot_lock:
        if _snapshot_cache and (now - _snapshot_cache_time) < CACHE_SECONDS:
            return _snapshot_cache

    # Construir nuevo snapshot
    client = _get_client()
    if client is None:
        empty = {"icmp": {}, "traffic": {}, "health": {}, "tcp": {}}
        with _snapshot_lock:
            _snapshot_cache = empty
            _snapshot_cache_time = now
        return empty

    cfg = get_influx_config()
    bucket = cfg["bucket"]

    snapshot = {
        "icmp": _query_last_icmp(client, bucket),
        "traffic": _query_last_traffic(client, bucket),
        "health": _query_last_health(client, bucket),
        "tcp": _query_last_tcp(client, bucket),
    }

    with _snapshot_lock:
        _snapshot_cache = snapshot
        _snapshot_cache_time = now

    return snapshot


# ============================================================
# CIERRE AL SALIR
# ============================================================
atexit.register(close)