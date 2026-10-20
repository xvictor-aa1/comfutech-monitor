#sistema\settings.py
"""
Django settings for sistema project.

Sistema de Monitoreo de Red - Comfutech Güigüe
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# RUTAS BASE
# ============================================================
# BASE_DIR = C:\proyecto-django
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar .env desde la raíz del proyecto (donde está manage.py)
# Intentamos primero en BASE_DIR, luego en el padre como fallback.
_ENV_FILE = BASE_DIR / ".env"
if not _ENV_FILE.exists():
    _ENV_FILE = BASE_DIR.parent / ".env"
load_dotenv(_ENV_FILE)

# ============================================================
# SEGURIDAD
# ============================================================
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-49)*57b#_wk-4!u4#x-x5@2pa-c(er0-u1u#!1bxm2kf=0*6tz"
)

# ⚠️ IMPORTANTE: la variable DEBE llamarse DEBUG, no DJANGO_DEBUG.
# Django ignora cualquier otra.
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ============================================================
# APLICACIONES
# ============================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Apps propias
    'inventario',
    'alertas',
    'monitoreo',
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sistema.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.comfutech_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'sistema.wsgi.application'

# ============================================================
# BASE DE DATOS
# ============================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv("DB_NAME", "monitoreo_red"),
        'USER': os.getenv("DB_USER", "root"),
        'PASSWORD': os.getenv("DB_PASSWORD", ""),
        'HOST': os.getenv("DB_HOST", "127.0.0.1"),
        'PORT': os.getenv("DB_PORT", "3306"),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ============================================================
# VALIDACIÓN DE CONTRASEÑAS
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================================
# INTERNACIONALIZACIÓN
# ============================================================
LANGUAGE_CODE = 'es-ve'
TIME_ZONE = 'America/Caracas'
USE_I18N = True
USE_TZ = True

# ============================================================
# ARCHIVOS ESTÁTICOS
# ============================================================
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ❌ Deprecado || Usar en Django 4.2
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ✅ Django 5.1+
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ============================================================
# EMAIL BACKEND (desde .env)
# ============================================================
# El resto de la configuración de email (host, port, etc.)
# ahora se carga desde la tabla `email_config` en runtime.
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
)

#EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
#EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
#EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
#EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"
#EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
#EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
#EMAIL_TIMEOUT = 10

#DEFAULT_FROM_EMAIL = os.getenv(
#    "DEFAULT_FROM_EMAIL",
#    "Comfutech Monitor <noreply@comfutech.local>"
#)

# ============================================================
# AUTENTICACIÓN
# ============================================================
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ============================================================
# CONFIGURACIÓN COMFUTECH
# ============================================================
# Grafana
#GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
#
# InfluxDB
#INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
#INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "").strip('"').strip("'")
#INFLUX_ORG = os.getenv("INFLUX_ORG", "comfutech")
#INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "metricas_red")
#
# Telegram
#TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
#TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
#TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "False").lower() == "true"
#
# Monitor
#MONITOR_ENABLED = os.getenv("MONITOR_ENABLED", "True").lower() == "true"
#SNMP_POLL_INTERVAL = int(os.getenv("SNMP_POLL_INTERVAL", "60"))
#HEALTH_POLL_INTERVAL = int(os.getenv("HEALTH_POLL_INTERVAL", "60"))
#ICMP_POLL_INTERVAL = int(os.getenv("ICMP_POLL_INTERVAL", "60"))
#
# ============================================================
# CONFIGURACIÓN RUNTIME (desde MySQL)
# ============================================================
# Los siguientes parámetros se leen desde la tabla system_config:
#   - GRAFANA_URL
#   - INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET
#   - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ENABLED
#   - MONITOR_ENABLED, SNMP_POLL_INTERVAL, HEALTH_POLL_INTERVAL, ICMP_POLL_INTERVAL
#
# Usa las funciones en core.runtime_config para acceder a ellos.
#
# El siguiente bloque aplica la config de email al arranque (best effort)
# para que funcione desde el primer momento. Si la BD falla, no rompe.
def _bootstrap_email_from_db():
    try:
        from core.runtime_config import apply_email_config_to_settings
        apply_email_config_to_settings()
    except Exception:
        pass

try:
    import sys
    # Solo ejecutar después de que la BD esté lista
    if "migrate" not in sys.argv and "makemigrations" not in sys.argv:
        _bootstrap_email_from_db()
except Exception:
    pass


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

import os as _os
LOG_LEVEL = _os.getenv("DJANGO_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "verbose": {
            "format": "{levelname} {asctime} {name} [{process:d}] {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "maxBytes": 5 * 1024 * 1024,  # 5 MB
            "backupCount": 3,             # hasta 3 archivos rotados
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "monitor_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "monitor.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        # Django
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",     # silencia las queries SQL
            "propagate": False,
        },
        # Monitor
        "monitoreo": {
            "handlers": ["console", "monitor_file"],
            "level": "INFO",
            "propagate": False,
        },
        # Terceros ruidosos
        "pysnmp": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "influxdb_client": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "urllib3": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "requests": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apscheduler": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
