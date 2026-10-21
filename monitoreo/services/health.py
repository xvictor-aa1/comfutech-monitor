# monitoreo/services/health.py
"""
Poller de Core Health y Radiofrecuencia.

- `poll_health()`: CPU, memoria y temperatura de equipos
  core/distribution.
- `poll_radio()`: frecuencia, capacidad RX/TX, señal, ruido, CCQ,
  etc. de equipos marcados como radio-enlace.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional

from inventario.models import Device
from . import alerts, influx_writer
from .snmp_client import snmp_get_multiple, to_float
from .chassis_oids import (
    CORE_ROLES,
    MIKROTIK_CPU_OIDS,
    get_available_health_metrics,
    get_resolved_oids,
    get_resolved_radio_oids,
)

log = logging.getLogger(__name__)


# ============================================================
# HELPERS
# ============================================================
def _utcnow() -> datetime:
    """
    Devuelve la hora actual en UTC como datetime naive.

    Returns:
        datetime: fecha/hora UTC sin tzinfo.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ============================================================
# LECTURA DE MÉTRICAS DE CHASIS
# ============================================================
def _get_chassis_metrics(device) -> Dict[str, Optional[float]]:
    """
    Consulta los OIDs de chasis del equipo y devuelve un dict con los
    valores procesados (cpu_pct, mem_pct, temp_c, uptime).

    Args:
        device: instancia de Device.

    Returns:
        dict: valores procesados. Puede faltar alguno si el OID no
              respondió o el modelo no lo tiene.
    """
    oids_map, vendor = get_resolved_oids(device)

    metric_names = list(oids_map.keys())
    oid_list = list(oids_map.values())

    values = snmp_get_multiple(device, oid_list)

    result: Dict[str, Optional[float]] = {}
    for name, val in zip(metric_names, values):
        result[name] = to_float(val)

    # --- CPU MikroTik: promedio multi-core ---
    if vendor == "mikrotik":
        cpu_vals = snmp_get_multiple(device, MIKROTIK_CPU_OIDS)
        cpu_nums = [to_float(v) for v in cpu_vals if v is not None]
        if cpu_nums:
            result["cpu_pct"] = sum(cpu_nums) / len(cpu_nums)
        else:
            # Fallback: si el OID propietario devuelve >100, se divide
            cpu = result.get("cpu_pct")
            if cpu is not None and cpu > 100:
                result["cpu_pct"] = cpu / 100.0
        result.pop("mem_free", None)

    # --- Memoria: derivar mem_pct si no viene directo ---
    if result.get("mem_pct") is None:
        used = result.get("mem_used")
        size = result.get("mem_size")
        free = result.get("mem_free")
        if used is not None and size and size > 0:
            result["mem_pct"] = (used / size) * 100.0
        elif used is not None and free is not None and (used + free) > 0:
            result["mem_pct"] = (used / (used + free)) * 100.0

    # --- Uptime: TimeTicks (centésimas de segundo) → segundos ---
    if result.get("uptime") is not None:
        result["uptime"] = result["uptime"] / 100.0

    return result


# ============================================================
# LECTURA DE MÉTRICAS DE RADIOFRECUENCIA
# ============================================================
def _get_radio_metrics(device) -> Dict[str, Optional[float]]:
    """
    Consulta los OIDs de radiofrecuencia del equipo y devuelve un
    dict con los valores procesados.

    Las claves del dict resultante son las definidas en RADIO_OIDS
    (freq_mhz, capacity_rx_kbps, capacity_tx_kbps, noise_dbm,
    signal_dbm, ccq_pct, tx_rate_mbps, rx_rate_mbps, sta_count).

    Args:
        device: instancia de Device.

    Returns:
        dict: valores de radio disponibles. Puede faltar alguno si
              el OID no respondió.
    """
    radio_oids = get_resolved_radio_oids(device)
    if not radio_oids:
        return {}

    metric_names = list(radio_oids.keys())
    oid_list = list(radio_oids.values())
    values = snmp_get_multiple(device, oid_list)

    result: Dict[str, Optional[float]] = {}
    for name, val in zip(metric_names, values):
        result[name] = to_float(val)

    return result


# ============================================================
# CICLO COMPLETO DE CHASIS
# ============================================================
def poll_health() -> dict:
    """
    Ciclo de polling de chasis para todos los equipos core/distribution.

    Omite equipos cuyo modelo/fabricante no tengan métricas disponibles.

    Returns:
        dict: estadísticas del ciclo (devices, errors, alerts, skipped,
              duration_s).
    """
    start = time.time()
    stats = {
        "devices": 0,
        "errors": 0,
        "alerts": 0,
        "skipped": 0,
        "duration_s": 0.0,
    }

    devices = Device.objects.filter(
        active=True, device_role__in=list(CORE_ROLES)
    ).select_related("device_model")

    now = _utcnow()

    for device in devices:
        # ¿Tiene métricas disponibles? Si no, saltar
        available = get_available_health_metrics(device)
        if not available:
            log.debug(
                "[%s] Sin OIDs de chasis disponibles para su modelo '%s' "
                "(vendor=%s). Se omite el polling.",
                device.name,
                device.device_model.name if device.device_model else "—",
                device.vendor,
            )
            stats["skipped"] += 1
            continue

        stats["devices"] += 1

        try:
            metrics = _get_chassis_metrics(device)
        except Exception as e:
            log.exception("Error polling chasis de %s: %s", device.name, e)
            stats["errors"] += 1
            continue

        # Escribir a InfluxDB
        try:
            influx_writer.write_health(
                device_name=device.name,
                ip=device.ip,
                role=device.device_role,
                vendor=device.vendor,
                metrics=metrics,
                timestamp=now,
            )
        except Exception as e:
            log.error("Error escribiendo health en InfluxDB: %s", e)

        # Evaluar alertas
        try:
            alerts.evaluate_metrics(device, {
                "cpu_pct": metrics.get("cpu_pct"),
                "mem_pct": metrics.get("mem_pct"),
                "temp_c": metrics.get("temp_c"),
            })
        except Exception as e:
            log.exception("Error evaluando alertas para %s: %s", device.name, e)

        log.info(
            "[%s] %s [%s] - CPU=%s%% MEM=%s%% TEMP=%s°C UPTIME=%s h",
            device.name, device.ip, device.device_role,
            f"{metrics['cpu_pct']:.1f}" if metrics.get("cpu_pct") is not None else "N/A",
            f"{metrics['mem_pct']:.1f}" if metrics.get("mem_pct") is not None else "N/A",
            f"{metrics['temp_c']:.1f}" if metrics.get("temp_c") is not None else "N/A",
            f"{metrics['uptime']/3600:.1f}" if metrics.get("uptime") else "N/A",
        )

    stats["duration_s"] = round(time.time() - start, 2)
    return stats


# ============================================================
# CICLO COMPLETO DE RADIOFRECUENCIA
# ============================================================
def poll_radio() -> dict:
    """
    Ciclo de polling de radiofrecuencia para equipos de radioenlace.

    Solo se ejecuta sobre equipos con `device_model.is_wireless_link=True`.
    Escribe en el measurement `radio` de InfluxDB y evalúa alertas sobre
    las métricas de radio (freq_mhz, capacity_rx_kbps, etc.).

    Returns:
        dict: estadísticas del ciclo (devices, errors, alerts, skipped,
              duration_s).
    """
    start = time.time()
    stats = {
        "devices": 0,
        "errors": 0,
        "alerts": 0,
        "skipped": 0,
        "duration_s": 0.0,
    }

    devices = Device.objects.filter(
        active=True,
        device_model__is_wireless_link=True,
    ).select_related("device_model")

    now = _utcnow()

    for device in devices:
        radio_oids = get_resolved_radio_oids(device)
        if not radio_oids:
            log.debug(
                "[%s] Sin OIDs de radio configurados. Se omite.",
                device.name,
            )
            stats["skipped"] += 1
            continue

        stats["devices"] += 1

        try:
            metrics = _get_radio_metrics(device)
        except Exception as e:
            log.exception("Error polling radio de %s: %s", device.name, e)
            stats["errors"] += 1
            continue

        # Escribir a InfluxDB
        try:
            influx_writer.write_radio(
                device_name=device.name,
                ip=device.ip,
                role=device.device_role,
                vendor=device.vendor,
                metrics=metrics,
                timestamp=now,
            )
        except Exception as e:
            log.error("Error escribiendo radio en InfluxDB: %s", e)

        # Evaluar alertas de radio
        try:
            alerts.evaluate_metrics(device, {
                "freq_mhz": metrics.get("freq_mhz"),
                "capacity_rx_kbps": metrics.get("capacity_rx_kbps"),
                "capacity_tx_kbps": metrics.get("capacity_tx_kbps"),
                "noise_dbm": metrics.get("noise_dbm"),
                "signal_dbm": metrics.get("signal_dbm"),
                "ccq_pct": metrics.get("ccq_pct"),
                "sta_count": metrics.get("sta_count"),
            })
        except Exception as e:
            log.exception(
                "Error evaluando alertas de radio para %s: %s",
                device.name, e,
            )

        log.info(
            "[%s] Radio: freq=%s MHz, capRX=%s kbps, capTX=%s kbps, "
            "signal=%s dBm, noise=%s dBm, CCQ=%s%%, clientes=%s",
            device.name,
            metrics.get("freq_mhz", "N/A"),
            metrics.get("capacity_rx_kbps", "N/A"),
            metrics.get("capacity_tx_kbps", "N/A"),
            metrics.get("signal_dbm", "N/A"),
            metrics.get("noise_dbm", "N/A"),
            metrics.get("ccq_pct", "N/A"),
            metrics.get("sta_count", "N/A"),
        )

    stats["duration_s"] = round(time.time() - start, 2)
    return stats