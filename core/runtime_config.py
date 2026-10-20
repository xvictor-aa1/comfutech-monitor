# core/runtime_config.py
"""
Carga perezosa de la configuración runtime desde MySQL.

Centraliza el acceso a:
  - SystemConfig (Grafana, InfluxDB, Telegram, Monitor)
  - EmailConfig (SMTP)

Todas las funciones usan caché en memoria que se invalida automáticamente
al guardar los modelos (ver core/signals.py).
"""
from threading import Lock

_cache = {}
_lock = Lock()


# ============================================================
# CACHÉ
# ============================================================
def reset_cache():
    """Limpia todo el caché. Se llama desde las signals."""
    with _lock:
        _cache.clear()


def _get(key: str, loader):
    """Devuelve del caché o carga y guarda."""
    with _lock:
        if key in _cache:
            return _cache[key]

    value = loader()

    with _lock:
        _cache[key] = value
    return value


# ============================================================
# SYSTEM CONFIG
# ============================================================
def _load_system_config():
    from core.models import SystemConfig
    return SystemConfig.get()


def get_system_config():
    return _get("system_config", _load_system_config)


def get_grafana_url() -> str:
    return get_system_config().grafana_url or "http://localhost:3000"


def get_influx_config() -> dict:
    cfg = get_system_config()
    return {
        "url": cfg.influx_url or "http://localhost:8086",
        "token": cfg.influx_token or "",
        "org": cfg.influx_org or "comfutech",
        "bucket": cfg.influx_bucket or "metricas_red",
    }


def get_telegram_config() -> dict:
    cfg = get_system_config()
    return {
        "enabled": bool(cfg.telegram_enabled),
        "bot_token": cfg.telegram_bot_token or "",
        "chat_id": cfg.telegram_chat_id or "",
    }


def get_monitor_config() -> dict:
    cfg = get_system_config()
    return {
        "enabled": bool(cfg.monitor_enabled),
        "snmp_poll_interval": int(cfg.snmp_poll_interval or 60),
        "health_poll_interval": int(cfg.health_poll_interval or 120),
        "icmp_poll_interval": int(cfg.icmp_poll_interval or 120),
    }


# ============================================================
# EMAIL CONFIG
# ============================================================
def _load_email_config():
    from core.models import EmailConfig
    return EmailConfig.get()


def get_email_config() -> dict:
    def loader():
        cfg = _load_email_config()
        return {
            "host": cfg.email_host or "localhost",
            "port": int(cfg.email_port or 587),
            "use_tls": bool(cfg.email_use_tls),
            "use_ssl": bool(cfg.email_use_ssl),
            "user": cfg.email_host_user or "",
            "password": cfg.email_host_password or "",
            "from_email": cfg.default_from_email or "noreply@comfutech.local",
        }
    return _get("email_config", loader)


def apply_email_config_to_settings():
    """Aplica la config de email al módulo django.conf.settings en runtime."""
    from django.conf import settings as dj_settings
    cfg = get_email_config()

    dj_settings.EMAIL_HOST = cfg["host"]
    dj_settings.EMAIL_PORT = cfg["port"]
    dj_settings.EMAIL_USE_TLS = cfg["use_tls"]
    dj_settings.EMAIL_USE_SSL = cfg["use_ssl"]
    dj_settings.EMAIL_HOST_USER = cfg["user"]
    dj_settings.EMAIL_HOST_PASSWORD = cfg["password"]
    dj_settings.DEFAULT_FROM_EMAIL = cfg["from_email"]