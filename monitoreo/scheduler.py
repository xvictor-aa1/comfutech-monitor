# monitoreo/scheduler.py
"""
Scheduler APScheduler con auto-reload de config y modo silencioso.

Jobs:
  - traffic: SNMP Tráfico (intervalo configurable)
  - health:  Core Health (intervalo configurable)
  - icmp:    ICMP/TCP (intervalo configurable)
  - radio:   Radiofrecuencia (mismo intervalo que health)
  - heartbeat: actualiza el estado y recarga la config
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

# Job IDs activos
_JOB_IDS = ("traffic", "health", "icmp", "radio", "ap_clients")


def _utcnow_aware():
    """Devuelve la hora actual en UTC con tzinfo."""
    return datetime.now(timezone.utc)


# ============================================================
# SILENCIO
# ============================================================
def silence_noisy_loggers():
    """Reduce el nivel de loggers ruidosos."""
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
    """Activa/desactiva el modo silencioso."""
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
    """Actualiza el heartbeat y detecta cambios de configuración."""
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
    """Ejecuta el poller de tráfico SNMP."""
    from .services.traffic import poll_traffic
    try:
        stats = poll_traffic()
        log.info("Traffic poll OK: %s", stats)
        _update_status("last_traffic_run")
    except Exception as e:
        log.exception("Traffic poll falló: %s", e)
        _update_status("last_traffic_run", error=f"Traffic: {e}")


def _job_health():
    """Ejecuta el poller de Core Health."""
    from .services.health import poll_health
    try:
        stats = poll_health()
        log.info("Health poll OK: %s", stats)
        _update_status("last_health_run")
    except Exception as e:
        log.exception("Health poll falló: %s", e)
        _update_status("last_health_run", error=f"Health: {e}")


def _job_icmp():
    """Ejecuta el poller ICMP/TCP."""
    from .services.icmp_tcp import poll_icmp_tcp
    try:
        stats = poll_icmp_tcp()
        log.info("ICMP/TCP poll OK: %s", stats)
        _update_status("last_icmp_run")
    except Exception as e:
        log.exception("ICMP/TCP poll falló: %s", e)
        _update_status("last_icmp_run", error=f"ICMP/TCP: {e}")


def _job_radio():
    """Ejecuta el poller de radiofrecuencia (solo equipos wireless)."""
    from .services.radio import poll_radio
    try:
        stats = poll_radio()
        log.info("Radio poll OK: %s", stats)
        _update_status("last_radio_run")
    except Exception as e:
        log.exception("Radio poll falló: %s", e)
        _update_status("last_radio_run", error=f"Radio: {e}")


def _job_ap_clients():
    """Ejecuta el poller de clientes AP."""
    from .services.ap_clients import poll_ap_clients
    try:
        stats = poll_ap_clients()
        log.info("AP Clients poll OK: %s", stats)
        _update_status("last_ap_clients_run")
    except Exception as e:
        log.exception("AP Clients poll falló: %s", e)
        _update_status("last_ap_clients_run", error=f"AP Clients: {e}")


def _update_status(field: str, error: str = None):
    """Actualiza un campo de fecha de último run en MonitorStatus."""
    from .models import MonitorStatus
    try:
        MonitorStatus.objects.filter(id=1).update(**{field: dj_tz.now()})
        if error:
            MonitorStatus.objects.filter(id=1).update(last_error=error)
    except Exception:
        pass


# ============================================================
# AUTO-RELOAD DE CONFIG
# ============================================================
def _check_config_changes():
    """Detecta cambios en SystemConfig y los aplica al scheduler."""
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

    # Intervalos: traffic / health / icmp / radio / ap_clients
    if current["snmp_poll_interval"] != _config_snapshot["snmp_poll_interval"]:
        try:
            _scheduler.modify_job("traffic", seconds=current["snmp_poll_interval"])
            log.info("Job 'traffic' → %ds.", current["snmp_poll_interval"])
        except Exception as e:
            log.error("No se pudo modificar 'traffic': %s", e)

    if current["health_poll_interval"] != _config_snapshot["health_poll_interval"]:
        # health, radio y ap_clients comparten intervalo
        for job_id in ("health", "radio", "ap_clients"):
            try:
                _scheduler.modify_job(job_id, seconds=current["health_poll_interval"])
                log.info("Job '%s' → %ds.", job_id, current["health_poll_interval"])
            except Exception as e:
                log.error("No se pudo modificar '%s': %s", job_id, e)

    if current["icmp_poll_interval"] != _config_snapshot["icmp_poll_interval"]:
        try:
            _scheduler.modify_job("icmp", seconds=current["icmp_poll_interval"])
            log.info("Job 'icmp' → %ds.", current["icmp_poll_interval"])
        except Exception as e:
            log.error("No se pudo modificar 'icmp': %s", e)

    _config_snapshot = current


def _pause_all_jobs():
    """Pausa todos los jobs."""
    for job_id in _JOB_IDS:
        try:
            _scheduler.pause_job(job_id)
        except Exception:
            pass


def _resume_all_jobs():
    """Reanuda todos los jobs."""
    for job_id in _JOB_IDS:
        try:
            _scheduler.resume_job(job_id)
        except Exception:
            pass


# ============================================================
# START / STOP / RESTART
# ============================================================
def start_scheduler():
    """Inicia el scheduler y programa todos los jobs."""
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

    _scheduler.add_job(
        _job_traffic, "interval",
        seconds=cfg["snmp_poll_interval"],
        id="traffic", name="SNMP Traffic Poller",
    )
    _scheduler.add_job(
        _job_health, "interval",
        seconds=cfg["health_poll_interval"],
        id="health", name="Core Health Poller",
    )
    _scheduler.add_job(
        _job_icmp, "interval",
        seconds=cfg["icmp_poll_interval"],
        id="icmp", name="ICMP/TCP Poller",
    )
    _scheduler.add_job(
        _job_radio, "interval",
        seconds=cfg["health_poll_interval"],
        id="radio", name="RF Radio Poller",
    )
    _scheduler.add_job(
        _job_ap_clients, "interval",
        seconds=cfg["health_poll_interval"],
        id="ap_clients", name="AP Clients Poller",
    )
    _scheduler.add_job(
        _heartbeat_and_reload, "interval",
        seconds=60, id="heartbeat", name="Heartbeat + Config reload",
    )

    _scheduler.start()

    if not cfg["enabled"]:
        _pause_all_jobs()
        log.warning("Monitor iniciado DESHABILITADO.")
    else:
        for job_id in _JOB_IDS:
            try:
                _scheduler.modify_job(job_id, next_run_time=_utcnow_aware())
            except Exception:
                pass

    _config_snapshot = cfg

    log.info(
        "Scheduler iniciado: traffic=%ds, health=%ds, icmp=%ds, "
        "radio=%ds, enabled=%s.",
        cfg["snmp_poll_interval"], cfg["health_poll_interval"],
        cfg["icmp_poll_interval"], cfg["health_poll_interval"],
        cfg["enabled"],
    )
    return _scheduler


def stop_scheduler():
    """Detiene el scheduler."""
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
    """Reinicia el scheduler (stop + reset cliente InfluxDB + start)."""
    stop_scheduler()
    from .services import influx_writer
    influx_writer.reset()
    return start_scheduler()