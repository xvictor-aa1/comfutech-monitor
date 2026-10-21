# monitoreo/services/chassis_oids.py
"""
Diccionario de OIDs de chasis y radiofrecuencia por fabricante.

Responsabilidades:
  - Definir OIDs por defecto de chasis (CPU, memoria, temperatura).
  - Definir OIDs por defecto de radiofrecuencia (frecuencia, capacidad
    RX/TX, señal, ruido, CCQ, etc.) para fabricantes de radioenlaces.
  - Exponer helpers para resolver qué OIDs usar en cada equipo,
    priorizando los OIDs del modelo sobre los del fabricante.
"""

# ============================================================
# OIDs DE CHASIS (CPU, MEM, TEMP) - GENÉRICOS
# ============================================================
CHASSIS_OIDS = {
    "cisco": {
        "cpu_pct":  "1.3.6.1.4.1.9.9.109.1.1.1.1.5.1",
        "mem_pct":  "1.3.6.1.4.1.9.9.48.1.1.1.5.1",
        "mem_free": "1.3.6.1.4.1.9.9.48.1.1.1.6.1",
        "temp_c":   "1.3.6.1.4.1.9.9.13.1.3.1.3.1",
    },
    "mikrotik": {
        "cpu_pct":  "1.3.6.1.4.1.14988.1.1.3.10.0",
        "mem_used": "1.3.6.1.2.1.25.2.3.1.6.65536",
        "mem_size": "1.3.6.1.2.1.25.2.3.1.5.65536",
        "temp_c":   "1.3.6.1.4.1.14988.1.1.3.100.1.3.14",
        "uptime":   "1.3.6.1.2.1.1.3.0",
    },
    "huawei": {
        "cpu_pct":  "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.5.1",
        "mem_pct":  "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.7.1",
        "temp_c":   "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.11.1",
    },
    "ubiquiti": {
        # CPU y temperatura genéricos para equipos AirOS/AirMax
        "cpu_pct":  "1.3.6.1.4.1.41112.1.4.8.3.0",
        "temp_c":   "1.3.6.1.4.1.41112.1.4.8.4.0",
        "mem_pct":  "1.3.6.1.4.1.41112.1.4.5.1.5.1",  # puede variar
    },
    "cambium": {
        "cpu_pct":  "1.3.6.1.4.1.17713.21.2.1.64.0",
    },
    "generic": {
        "mem_used": "1.3.6.1.2.1.25.2.3.1.6.1",
        "mem_size": "1.3.6.1.2.1.25.2.3.1.5.1",
    },
}

# ============================================================
# OIDs DE RADIOFRECUENCIA (para radioenlaces)
# ============================================================
RADIO_OIDS = {
    "ubiquiti": {
        # Frecuencia de operación
        "freq_mhz":         "1.3.6.1.4.1.41112.1.4.1.1.4",
        # Capacidad de la estación (punto a punto / estación única)
        "capacity_rx_kbps": "1.3.6.1.4.1.41112.1.4.7.1.18.1",
        "capacity_tx_kbps": "1.3.6.1.4.1.41112.1.4.7.1.19.1",
        # Estadísticas wireless (ubntWlStat)
        "noise_dbm":        "1.3.6.1.4.1.41112.1.4.5.1.8.1",
        "signal_dbm":       "1.3.6.1.4.1.41112.1.4.5.1.5.1",
        "ccq_pct":          "1.3.6.1.4.1.41112.1.4.5.1.7.1",
        "tx_rate_mbps":     "1.3.6.1.4.1.41112.1.4.5.1.9.1",
        "rx_rate_mbps":     "1.3.6.1.4.1.41112.1.4.5.1.10.1",
        "sta_count":        "1.3.6.1.4.1.41112.1.4.5.1.15.1",
    },
    # Otros fabricantes de radio pueden añadirse aquí.
}

# OIDs multi-core específicos de MikroTik RouterOS 7
MIKROTIK_CPU_OIDS = [
    "1.3.6.1.2.1.25.3.3.1.2.1",
    "1.3.6.1.2.1.25.3.3.1.2.2",
    "1.3.6.1.2.1.25.3.3.1.2.3",
    "1.3.6.1.2.1.25.3.3.1.2.4",
]

# OIDs comunes a todos los fabricantes
COMMON_OIDS = {
    "uptime": "1.3.6.1.2.1.1.3.0",
}

# Roles que reciben polling de chasis
CORE_ROLES = {"core", "distribution"}


# ============================================================
# HELPERS
# ============================================================
def get_resolved_oids(device) -> tuple:
    """
    Devuelve los OIDs de chasis efectivos y el vendor en minúsculas.

    Prioridad:
      1. OIDs del modelo del equipo (`device.device_model.oids`).
      2. OIDs por defecto del fabricante (`CHASSIS_OIDS[vendor]`).

    Args:
        device: instancia de `inventario.models.Device`.

    Returns:
        tuple: (oids_map: dict, vendor: str)
    """
    vendor = (device.vendor or "generic").lower()

    # Priorizar OIDs del modelo si están definidos y no vacíos
    if device.device_model and device.device_model.oids:
        oids_map = dict(device.device_model.oids)
    else:
        oids_map = dict(CHASSIS_OIDS.get(vendor, CHASSIS_OIDS["generic"]))

    # Asegurar que uptime siempre esté presente
    if "uptime" not in oids_map:
        oids_map["uptime"] = COMMON_OIDS["uptime"]

    # Eliminar entradas vacías (None o "")
    oids_map = {k: v for k, v in oids_map.items() if v}

    return oids_map, vendor


def get_resolved_radio_oids(device) -> dict:
    """
    Devuelve los OIDs de radiofrecuencia efectivos para un equipo.

    Prioriza los OIDs personalizados del modelo (que pueden incluir
    claves como 'freq_mhz', 'capacity_rx_kbps', etc.). Si el modelo
    no define OIDs de radio, usa los del fabricante en `RADIO_OIDS`.

    Args:
        device: instancia de `inventario.models.Device`.

    Returns:
        dict: {clave_metrica: oid} solo con las métricas de radio
              disponibles.
    """
    vendor = (device.vendor or "generic").lower()

    # Construir el conjunto de claves de radio conocidas
    radio_keys = set()
    for v_oids in RADIO_OIDS.values():
        radio_keys.update(v_oids.keys())

    # Priorizar OIDs personalizados del modelo
    if device.device_model and device.device_model.oids:
        custom_radio = {
            k: v for k, v in device.device_model.oids.items()
            if k in radio_keys and v
        }
        if custom_radio:
            return custom_radio

    # Fallback a los OIDs del fabricante
    return dict(RADIO_OIDS.get(vendor, {}))


def get_available_health_metrics(device) -> list:
    """
    Devuelve la lista de métricas de chasis que se PUEDEN consultar
    en este equipo, basándose en los OIDs resueltos.

    Considera:
      - Que el rol del equipo sea core/distribution (si no, no se
        hace polling de chasis y devuelve lista vacía).
      - Que el modelo o el fabricante tengan OIDs para cpu, memoria
        y/o temperatura.
      - Casos especiales como MikroTik (CPU multi-core siempre disponible).

    Args:
        device: instancia de `inventario.models.Device`.

    Returns:
        list: métricas disponibles entre {"cpu_pct", "mem_pct", "temp_c"}.
              Lista vacía si no se puede consultar ninguna.
    """
    # Si el rol no es core/distribution, no se hace polling de chasis
    if device.device_role not in CORE_ROLES:
        return []

    oids_map, vendor = get_resolved_oids(device)
    available = []

    # --- CPU ---
    if vendor == "mikrotik":
        # MikroTik: siempre disponible vía MIKROTIK_CPU_OIDS (multi-core)
        available.append("cpu_pct")
    elif oids_map.get("cpu_pct") or oids_map.get("cpu_load"):
        available.append("cpu_pct")

    # --- Memoria ---
    has_mem_pct = bool(oids_map.get("mem_pct"))
    has_mem_used = bool(oids_map.get("mem_used"))
    has_mem_size = bool(oids_map.get("mem_size") or oids_map.get("mem_free"))
    if has_mem_pct or (has_mem_used and has_mem_size):
        available.append("mem_pct")

    # --- Temperatura ---
    if oids_map.get("temp_c"):
        available.append("temp_c")

    return available


def get_available_radio_metrics(device) -> list:
    """
    Devuelve la lista de métricas de radiofrecuencia disponibles
    para el equipo, basándose en sus OIDs resueltos.

    Args:
        device: instancia de `inventario.models.Device`.

    Returns:
        list: claves de métricas de radio disponibles (p.ej.
              ["freq_mhz", "capacity_rx_kbps", ...]).
    """
    radio_oids = get_resolved_radio_oids(device)
    return list(radio_oids.keys())


def has_meaningful_health_metrics(device) -> bool:
    """
    Devuelve True si el equipo tiene al menos UNA métrica de chasis
    que vale la pena mostrar en el dashboard (cpu, memoria o temperatura).

    Args:
        device: instancia de `inventario.models.Device`.

    Returns:
        bool: True si hay al menos cpu/mem/temp disponible.
    """
    return len(get_available_health_metrics(device)) > 0