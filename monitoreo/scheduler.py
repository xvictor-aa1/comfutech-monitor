# monitoreo/scheduler.py
"""
Scheduler APScheduler con auto-reload de config y modo silencioso.

Jobs registrados:
  - traffic:   SNMP Traffic Poller (cada N segundos).
  - health:    Core Health Poller (cada N segundos).
  - radio:     Radio Poller (cada N segundos).
  - icmp:      ICMP/TCP Poller (cada N segundos).
  - heartbeat: Heartbeat + Config reload (cada 60s).
"""
import logging
import os
import socket
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone as dj_tz

from core.runtime_config import get_monitor_config

log = logging.getLogger(__name__)

_scheduler = None
_config_snapshot = None


def _utcnow_aware():
    """
    Devuelve la hora actual en UTC con tzinfo.

    Returns:
        datetime: fecha/hora UTC aware.
    """
    return datetime.now(timezone.utc)


# ============================================================
# SILENCIO
# ============================================================
def silence_noisy_loggers():
    """
    Reduce el nivel de loggers ruidosos a WARNING.

    Útil para el modo `--silent` del comando `run_monitor`.
    """
    noisy = {
        "pysnmp": logging.WARNING,
        "pysnmp.entity": logging.WARNING,
        "pysnmp.carrier": logging.WARNING,
        "influxdb_client": logging.WARNING,
        "urllib3": logging.WARNING,
        "requests": logging.WARNING,
        "apscheduler": logging.WARNING,
        "apscheduler.executors": logging.WARNING,
        "apscheduler.scheduler": logging.WARNING,
        "django.db.backends": logging.WARNING,
    }
    for name, level in noisy.items():
        logging.getLogger(name).setLevel(level)


def set_silent_mode(enabled: bool = True):
    """
    Activa/desactiva el modo silencioso.

    Args:
        enabled: si True, baja el nivel de log a WARNING+ para los
                 loggers del proyecto.
    """
    silence_noisy_loggers()

    if enabled:
        for name in ("monitoreo", "core", "inventario", "alertas"):
            logging.getLogger(name).setLevel(logging.WARNING)
        log.warning("Modo silencioso ACTIVADO (solo WARNING+).")
    else:
        for name in ("monitoreo", "core", "inventario", "alertas"):
            logging.getLogger(name).setLevel(logging.INFO)
        log.info("Modo silencioso DESACTIVADO (INFO+).")


# ============================================================
# JOBS
# ============================================================
def _heartbeat_and_reload():
    """
    Actualiza el heartbeat del monitor y comprueba cambios de config.

    - Escribe `MonitorStatus.last_heartbeat` y estado en la BD.
    - Llama a `_check_config_changes()` para aplicar cambios de
      intervalos o habilitación sin reiniciar el proceso.
    """
    from .models import MonitorStatus
    try:
        MonitorStatus.objects.update_or_create(
            id=1,
            defaults={
                "last_heartbeat": dj_tz.now(),
                "status": "running",
                "hostname": socket.gethostname(),
                "pid": os.getpid(),
            },
        )
    except Exception as e:
        log.error("Heartbeat falló: %s", e)

    try:
        _check_config_changes()
    except Exception as e:
        log.error("Fallo comprobando cambios: %s", e)


def _job_traffic():
    """
    Ejecuta el poller de tráfico SNMP y actualiza el estado.
    """
    from .services.traffic import poll_traffic
    try:
        stats = poll_traffic()
        log.info("Traffic poll OK: %s", stats)
        _update_status("last_traffic_run")
    except Exception as e:
        log.exception("Traffic poll falló: %s", e)
        _update_status("last_traffic_run", error=f"Traffic: {e}")


def _job_health():
    """
    Ejecuta el poller de chasis y actualiza el estado.
    """
    from .services.health import poll_health
    try:
        stats = poll_health()
        log.info("Health poll OK: %s", stats)
        _update_status("last_health_run")
    except Exception as e:
        log.exception("Health poll falló: %s", e)
        _update_status("last_health_run", error=f"Health: {e}")


def _job_radio():
    """
    Ejecuta el poller de radiofrecuencia y actualiza el estado.
    """
    from .services.health import poll_radio
    try:
        stats = poll_radio()
        log.info("Radio poll OK: %s", stats)
        _update_status("last_radio_run")  # Requiere migración menor si no existe
    except Exception as e:
        log.exception("Radio poll falló: %s", e)
        _update_status("last_radio_run", error=f"Radio: {e}")


def _job_icmp():
    """
    Ejecuta el poller ICMP/TCP y actualiza el estado.
    """
    from .services.icmp_tcp import poll_icmp_tcp
    try:
        stats = poll_icmp_tcp()
        log.info("ICMP/TCP poll OK: %s", stats)
        _update_status("last_icmp_run")
    except Exception as e:
        log.exception("ICMP/TCP poll falló: %s", e)
        _update_status("last_icmp_run", error=f"ICMP/TCP: {e}")


def _update_status(field: str, error: str = None):
    """
    Actualiza un campo de fecha en `MonitorStatus` y opcionalmente
    el último error.

    Args:
        field: nombre del campo a actualizar (p.ej. "last_traffic_run").
        error: mensaje de error opcional.
    """
    from .models import MonitorStatus
    try:
        MonitorStatus.objects.filter(id=1).update(**{field: dj_tz.now()})
        if error:
            MonitorStatus.objects.filter(id=1).update(last_error=error)
    except Exception:
        pass


# ============================================================
# AUTO-RELOAD
# ============================================================
def _check_config_changes():
    """
    Comprueba si la configuración del monitor cambió y aplica los
    cambios sin reiniciar el proceso.

    - Si `enabled` cambia, pausa o reanuda los jobs.
    - Si cambian los intervalos, modifica los jobs con
      `_scheduler.modify_job`.
    """
    global _config_snapshot

    current = get_monitor_config()

    if _config_snapshot is None:
        _config_snapshot = current
        return

    if current == _config_snapshot:
        return

    changed = [k for k in current if current[k] != _config_snapshot.get(k)]
    log.info("Config cambió: %s", ", ".join(changed))

    if current["enabled"] != _config_snapshot["enabled"]:
        if not current["enabled"]:
            log.warning("Monitor deshabilitado. Pausando jobs.")
            _pause_all_jobs()
        else:
            log.info("Monitor reactivado.")
            _resume_all_jobs()

    intervals = {
        "snmp_poll_interval":   ("traffic", current["snmp_poll_interval"]),
        "health_poll_interval": ("health",  current["health_poll_interval"]),
        "icmp_poll_interval":   ("icmp",    current["icmp_poll_interval"]),
    }
    for key, (job_id, seconds) in intervals.items():
        if current[key] != _config_snapshot[key]:
            try:
                _scheduler.modify_job(job_id, seconds=seconds)
                log.info("Job '%s' → %ds.", job_id, seconds)
            except Exception as e:
                log.error("No se pudo modificar '%s': %s", job_id, e)

    _config_snapshot = current


def _pause_all_jobs():
    """
    Pausa todos los jobs de polling.
    """
    for job_id in ("traffic", "health", "radio", "icmp"):
        try:
            _scheduler.pause_job(job_id)
        except Exception:
            pass


def _resume_all_jobs():
    """
    Reanuda todos los jobs de polling.
    """
    for job_id in ("traffic", "health", "radio", "icmp"):
        try:
            _scheduler.resume_job(job_id)
        except Exception:
            pass


# ============================================================
# START / STOP / RESTART
# ============================================================
def start_scheduler():
    """
    Inicia el scheduler con los jobs configurados.

    - Reinicia el warm-up del motor de alertas.
    - Crea los jobs de tráfico, chasis, radio, ICMP y heartbeat.
    - Si el monitor está deshabilitado, pausa los jobs.

    Returns:
        BackgroundScheduler: instancia del scheduler.
    """
    global _scheduler, _config_snapshot

    if _scheduler is not None:
        return _scheduler

    # Reiniciar warm-up del motor de alertas
    try:
        from .services import alerts as alerts_service
        alerts_service.reset_startup_time()
    except Exception:
        pass

    cfg = get_monitor_config()

    _scheduler = BackgroundScheduler(
        timezone="UTC",
        job_defaults={
            "max_instances": 1,
            "coalesce": True,
            "misfire_grace_time": 30,
        },
    )

    # Job de tráfico
    _scheduler.add_job(
        _job_traffic, "interval",
        seconds=cfg["snmp_poll_interval"],
        id="traffic", name="SNMP Traffic Poller",
    )
    # Job de chasis
    _scheduler.add_job(
        _job_health, "interval",
        seconds=cfg["health_poll_interval"],
        id="health", name="Core Health Poller",
    )
    # Job de radio (mismo intervalo que health)
    _scheduler.add_job(
        _job_radio, "interval",
        seconds=cfg["health_poll_interval"],
        id="radio", name="Radio Poller",
    )
    # Job de ICMP/TCP
    _scheduler.add_job(
        _job_icmp, "interval",
        seconds=cfg["icmp_poll_interval"],
        id="icmp", name="ICMP/TCP Poller",
    )
    # Heartbeat
    _scheduler.add_job(
        _heartbeat_and_reload, "interval",
        seconds=60, id="heartbeat", name="Heartbeat + Config reload",
    )

    _scheduler.start()

    if not cfg["enabled"]:
        _pause_all_jobs()
        log.warning("Monitor iniciado DESHABILITADO.")
    else:
        for job_id in ("traffic", "health", "radio", "icmp"):
            try:
                _scheduler.modify_job(job_id, next_run_time=_utcnow_aware())
            except Exception:
                pass

    _config_snapshot = cfg

    log.info(
        "Scheduler iniciado: traffic=%ds, health=%ds, radio=%ds, "
        "icmp=%ds, enabled=%s.",
        cfg["snmp_poll_interval"], cfg["health_poll_interval"],
        cfg["health_poll_interval"],
        cfg["icmp_poll_interval"], cfg["enabled"],
    )
    return _scheduler


def stop_scheduler():
    """
    Detiene el scheduler y limpia el snapshot de configuración.
    """
    global _scheduler, _config_snapshot
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
            log.info("Scheduler detenido.")
        except Exception as e:
            log.error("Error deteniendo el scheduler: %s", e)
        _scheduler = None
        _config_snapshot = None


def restart_scheduler():
    """
    Reinicia el scheduler y el cliente de InfluxDB.

    Returns:
        BackgroundScheduler: el nuevo scheduler.
    """
    stop_scheduler()
    from .services import influx_writer
    influx_writer.reset()
    return start_scheduler()