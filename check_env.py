# check_env.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
env_file = BASE_DIR / ".env"

print(f"Buscando .env en: {env_file}")
print(f"¿Existe? {env_file.exists()}")
print()

load_dotenv(env_file)

keys_to_check = [
    "DJANGO_SECRET_KEY",
    "DJANGO_DEBUG",
    "DJANGO_ALLOWED_HOSTS",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_PORT",
    "INFLUX_URL",
    "INFLUX_TOKEN",
    "INFLUX_ORG",
    "INFLUX_BUCKET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TELEGRAM_ENABLED",
    "GRAFANA_URL",
    "MONITOR_ENABLED",
]

for key in keys_to_check:
    val = os.getenv(key)
    if key in ("DJANGO_SECRET_KEY", "INFLUX_TOKEN", "TELEGRAM_BOT_TOKEN"):
        val = f"{val[:20]}..." if val else None
    print(f"  {key} = {val!r}")

print()
print(f"DEBUG interpretado: {os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'}")
