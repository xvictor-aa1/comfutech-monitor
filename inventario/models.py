# inventario/models.py
from django.db import models


# ============================================================
# MODELO DE EQUIPO (Fabricante + Modelo + OIDs)
# ============================================================
class DeviceModel(models.Model):
    """
    Modelo específico de un fabricante, con sus OIDs SNMP propios.

    Se usa para que al seleccionar un modelo en un Device, se carguen
    automáticamente las OIDs correctas para el polling de chasis
    (CPU, memoria, temperatura, etc.).
    """
    VENDOR_CHOICES = [
        ("MikroTik",  "MikroTik"),
        ("Ubiquiti",  "Ubiquiti"),
        ("Cambium",   "Cambium Networks"),
        ("Huawei",    "Huawei"),
        ("TP-Link",   "TP-Link"),
        ("Cisco",     "Cisco"),
        ("Mimosa",    "Mimosa Networks"),
        ("Engenius",  "EnGenius"),
        ("Otro",      "Otro"),
    ]

    vendor = models.CharField(
        max_length=50,
        choices=VENDOR_CHOICES,
        verbose_name="Fabricante",
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Modelo",
        help_text="Ej: RB4011iGS+, AirMax LiteBeam M5, ePMP 1000",
    )
    oids = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="OIDs específicos",
        help_text=(
            "Diccionario de OIDs propios de este modelo. "
            "Claves válidas: cpu_pct, mem_pct, mem_used, mem_size, "
            "mem_free, temp_c, uptime. "
            "Si está vacío, se usarán las OIDs por defecto del fabricante."
        ),
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción",
        help_text="Notas opcionales sobre el modelo (firmware, características, etc.)",
    )
    is_wireless_link = models.BooleanField(
        default=False,
        verbose_name="Es radio-enlace",
        help_text=(
            "Marcar si este modelo es un equipo de radio-enlace "
            "(AirMax, Cambium, Mimosa, etc.). Los equipos con este "
            "flag habilitan el monitoreo de Utilización de Enlace."
        ),
    )
    active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "device_models"
        unique_together = [("vendor", "name")]
        ordering = ["vendor", "name"]
        verbose_name = "Modelo de equipo"
        verbose_name_plural = "Modelos de equipos"

    def __str__(self):
        return f"{self.vendor} - {self.name}"

    @property
    def has_custom_oids(self):
        """Devuelve True si el modelo define OIDs propias."""
        return bool(self.oids)


# ============================================================
# EQUIPO
# ============================================================
class Device(models.Model):
    """Equipo de red monitoreado (router, switch, CPE, firewall)."""

    TYPE_CHOICES = [
        ("router",    "Router"),
        ("switch",    "Switch"),
        ("cpe",       "CPE"),
        ("firewall",  "Firewall"),
        ("ap",        "Access Point"),
        ("otro",      "Otro"),
    ]

    ROLE_CHOICES = [
        ("core",         "Core"),
        ("distribution", "Distribución"),
        ("access",       "Acceso"),
        ("cpe",          "CPE"),
    ]

    VENDOR_CHOICES = [
        ("MikroTik",  "MikroTik"),
        ("Ubiquiti",  "Ubiquiti"),
        ("Cambium",   "Cambium Networks"),
        ("Huawei",    "Huawei"),
        ("TP-Link",   "TP-Link"),
        ("Cisco",     "Cisco"),
        ("Mimosa",    "Mimosa Networks"),
        ("Engenius",  "EnGenius"),
        ("Otro",      "Otro"),
    ]

    # --- Identificación ---
    name = models.CharField(max_length=100, verbose_name="Nombre")
    ip = models.CharField(max_length=45, unique=True, verbose_name="Dirección IP")
    device_type = models.CharField(
        max_length=50, choices=TYPE_CHOICES,
        default="router", verbose_name="Tipo",
    )
    device_role = models.CharField(
        max_length=20, choices=ROLE_CHOICES,
        default="access", verbose_name="Rol",
    )
    vendor = models.CharField(
        max_length=50, choices=VENDOR_CHOICES,
        default="Otro", verbose_name="Fabricante",
    )
    device_model = models.ForeignKey(
        DeviceModel,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="devices",
        verbose_name="Modelo",
        help_text="Modelo específico del equipo (opcional, mejora el polling de chasis).",
    )
    location = models.CharField(
        max_length=100, default="Güigüe", verbose_name="Ubicación",
    )

    # --- SNMP ---
    snmp_version = models.CharField(
        max_length=10, default="2c", verbose_name="Versión SNMP",
    )
    snmp_community = models.CharField(
        max_length=100, default="public", verbose_name="Community",
    )
    snmp_user = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Usuario SNMPv3",
    )
    snmp_auth = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Auth Key",
    )
    snmp_priv = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Priv Key",
    )

    # --- Monitoreo ---
    tcp_ports = models.CharField(
        max_length=255, default="161", verbose_name="Puertos TCP",
        help_text="Separados por coma. Ej: 161,22,80",
    )

    # --- Estado ---
    active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "devices"
        ordering = ["name"]
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

    def __str__(self):
        return f"{self.name} ({self.ip})"

    # ------------------------------------------------------------
    # PROPIEDADES ÚTILES
    # ------------------------------------------------------------
    @property
    def has_chassis_monitoring(self):
        """Devuelve True si el rol recibe polling de chasis."""
        return self.device_role in ("core", "distribution")

    @property
    def monitored_interfaces_count(self):
        """Cantidad de interfaces marcadas para monitoreo."""
        return self.interfaces.filter(monitored=True).count()

    @property
    def total_interfaces_count(self):
        """Cantidad total de interfaces descubiertas."""
        return self.interfaces.count()

    @property
    def effective_oids(self):
        """
        Devuelve las OIDs efectivas para este equipo:
          1. OIDs del modelo si está asignado
          2. Fallback a OIDs del fabricante (manejado en el servicio)
        """
        if self.device_model and self.device_model.oids:
            return dict(self.device_model.oids)
        return {}


# ============================================================
# INTERFAZ
# ============================================================
class Interface(models.Model):
    """Interfaz de red de un equipo."""

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="interfaces",
        verbose_name="Equipo",
    )
    if_index = models.PositiveIntegerField(verbose_name="ifIndex")
    if_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Nombre",
    )
    if_alias = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Alias",
    )
    if_speed_bps = models.BigIntegerField(
        null=True, blank=True, verbose_name="Velocidad (bps)",
    )
    if_type = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Tipo",
    )
    admin_status = models.BooleanField(
        default=True, verbose_name="Admin status",
    )
    oper_status = models.BooleanField(
        default=True, verbose_name="Oper status",
    )
    monitored = models.BooleanField(
        default=False, verbose_name="Monitoreada",
        help_text="Si está marcada, su tráfico se consulta vía SNMP.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "interfaces"
        unique_together = [("device", "if_index")]
        ordering = ["device", "if_index"]
        verbose_name = "Interfaz"
        verbose_name_plural = "Interfaces"

    def __str__(self):
        return f"{self.device.name} - {self.if_name or 'if' + str(self.if_index)}"

    # ------------------------------------------------------------
    # PROPIEDADES ÚTILES
    # ------------------------------------------------------------
    @property
    def speed_mbps(self):
        """Velocidad en Mbps, o None si no está disponible."""
        if not self.if_speed_bps:
            return None
        return int(self.if_speed_bps / 1_000_000)

    @property
    def display_name(self):
        """Nombre a mostrar (nombre + alias si aplica)."""
        if self.if_alias:
            return f"{self.if_name or 'if' + str(self.if_index)} ({self.if_alias})"
        return self.if_name or f"if{self.if_index}"
