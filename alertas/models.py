# alertas/models.py
"""
Modelos de la app `alertas`.

Incluye:
  - AlertRule: regla configurable con 1-5 condicionales lógicos.
  - Alert: alerta generada por una regla.
  - Threshold: umbral legacy (mantenido por compatibilidad).
"""
from django.contrib.auth.models import User
from django.db import models


class AlertRule(models.Model):
    """
    Regla de alerta configurable.

    Una regla puede combinar 1-5 condicionales lógicos. Cada condicional
    especifica su propio equipo, métrica, operador, umbral y duración.
    Se combinan usando operadores lógicos (AND / OR) aplicados de izquierda
    a derecha:

        ((cond1) AND/OR (cond2)) AND/OR (cond3) ...

    Los condicionales se guardan como lista JSON en `conditionals`:

        [
          {
            "device_id": 1,
            "metric": "cpu_pct",
            "operator": "gte",
            "threshold": 75.0,
            "duration_sec": 60,
            "logic": null           # el primero no necesita lógica
          },
          {
            "device_id": 2,
            "metric": "packet_loss_pct",
            "operator": "gte",
            "threshold": 5.0,
            "duration_sec": 120,
            "logic": "AND"          # se combina con el anterior
          }
        ]
    """

    # Número máximo de condicionales por regla
    MAX_CONDITIONALS = 5

    # ------------------------------------------------------------
    # CHOICES
    # ------------------------------------------------------------
    METRIC_CHOICES = [
        ("device_down",      "Caída del dispositivo (sin ICMP)"),
        ("latency_ms",       "Latencia ICMP (ms)"),
        ("packet_loss_pct",  "Pérdida de paquetes (%)"),
        ("utilization_pct",  "Utilización de enlace (%)"),
        ("cpu_pct",          "CPU (%)"),
        ("mem_pct",          "Memoria (%)"),
        ("temp_c",           "Temperatura (°C)"),
    ]

    OPERATOR_CHOICES = [
        ("gt",  "Mayor que (>)"),
        ("gte", "Mayor o igual (>=)"),
        ("lt",  "Menor que (<)"),
        ("lte", "Menor o igual (<=)"),
        ("eq",  "Igual a (=)"),
    ]

    SEVERITY_CHOICES = [
        ("info",     "Información"),
        ("warning",  "Advertencia"),
        ("critical", "Crítica"),
    ]

    LOGIC_CHOICES = [
        ("AND", "Y (todas deben cumplirse)"),
        ("OR",  "O (al menos una debe cumplirse)"),
    ]

    # ------------------------------------------------------------
    # IDENTIFICACIÓN
    # ------------------------------------------------------------
    name = models.CharField(max_length=150, verbose_name="Nombre")
    description = models.TextField(blank=True, verbose_name="Descripción")

    # ------------------------------------------------------------
    # CONDICIONALES (JSON)
    # ------------------------------------------------------------
    conditionals = models.JSONField(
        default=list,
        verbose_name="Condicionales",
        help_text="Lista de condicionales lógicos (máx. 5).",
    )

    # ------------------------------------------------------------
    # COMPORTAMIENTO
    # ------------------------------------------------------------
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES, default="warning",
        verbose_name="Prioridad",
    )
    custom_message = models.TextField(
        blank=True, verbose_name="Mensaje personalizado",
        help_text=(
            "Si está vacío, se genera un mensaje automático. "
            "Placeholders: {rule_name}, {severity}, {device}, {ip}, "
            "{metric}, {value}, {threshold}, {device1}..{device5}, "
            "{metric1}..{metric5}, {value1}..{value5}, etc."
        ),
    )

    # Telegram
    telegram_enabled = models.BooleanField(
        default=True, verbose_name="Notificar por Telegram",
    )
    telegram_cooldown_sec = models.PositiveIntegerField(
        default=600, verbose_name="Cooldown Telegram (s)",
    )

    # Modos de disparo
    fire_once = models.BooleanField(
        default=False, verbose_name="Disparar solo una vez",
    )
    skip_on_startup = models.BooleanField(
        default=False, verbose_name="Omitir al iniciar el monitor",
    )

    # Estado
    enabled = models.BooleanField(default=True, verbose_name="Activa")

    # ------------------------------------------------------------
    # AUDITORÍA
    # ------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="alert_rules_created",
    )

    class Meta:
        db_table = "alert_rules"
        ordering = ["-updated_at"]
        verbose_name = "Regla de alerta"
        verbose_name_plural = "Reglas de alerta"

    def __str__(self):
        count = len(self.conditionals or [])
        return f"{self.name} ({count} condicional{'es' if count != 1 else ''})"

    # ============================================================
    # PROPIEDADES ÚTILES
    # ============================================================
    @property
    def conditionals_count(self) -> int:
        """Número de condicionales configurados."""
        return len(self.conditionals or [])

    @property
    def device_ids(self) -> list:
        """IDs únicos de equipos involucrados en los condicionales."""
        ids = []
        for c in self.conditionals or []:
            did = c.get("device_id")
            if did and did not in ids:
                ids.append(did)
        return ids

    @property
    def primary_device_id(self) -> int:
        """ID del primer equipo (para compatibilidad con código viejo)."""
        if not self.conditionals:
            return None
        return self.conditionals[0].get("device_id")

    @property
    def primary_device(self):
        """Instancia del primer equipo (lazy, sin caché)."""
        from inventario.models import Device
        did = self.primary_device_id
        if not did:
            return None
        return Device.objects.filter(pk=did).first()

    @property
    def primary_metric(self) -> str:
        """Primera métrica (para compatibilidad)."""
        if not self.conditionals:
            return ""
        return self.conditionals[0].get("metric", "")

    @property
    def active_alerts_count(self) -> int:
        """Alertas activas generadas por esta regla."""
        return self.alerts.filter(status="activa").count()

    @property
    def last_fired_at(self):
        """Fecha de la última alerta disparada."""
        last = self.alerts.order_by("-created_at").first()
        return last.created_at if last else None

    @property
    def total_fired_count(self) -> int:
        """Total histórico de alertas disparadas por esta regla."""
        return self.alerts.count()

    # ============================================================
    # HELPERS DE FORMULARIO
    # ============================================================
    @staticmethod
    def get_valid_operators(metric: str) -> list:
        """
        Devuelve los operadores válidos para una métrica.
        El primero es el default.
        """
        valid_map = {
            "device_down":      ["eq"],
            "latency_ms":       ["gte", "gt"],
            "packet_loss_pct":  ["gte", "gt"],
            "utilization_pct":  ["gte", "gt"],
            "cpu_pct":          ["gte", "gt"],
            "mem_pct":          ["gte", "gt"],
            "temp_c":           ["gte", "gt"],
        }
        ops = valid_map.get(metric, ["gte", "gt", "lt", "lte", "eq"])
        labels = dict(AlertRule.OPERATOR_CHOICES)
        return [(op, labels[op]) for op in ops if op in labels]

    def get_conditionals_with_devices(self) -> list:
        """
        Devuelve los condicionales enriquecidos con el objeto Device
        y etiquetas legibles. Se usa en templates.
        """
        from inventario.models import Device

        # Pre-cargar todos los devices
        ids = self.device_ids
        devices_map = {
            d.id: d for d in Device.objects.filter(id__in=ids)
        }

        result = []
        metric_labels = dict(self.METRIC_CHOICES)
        operator_labels = dict(self.OPERATOR_CHOICES)
        logic_labels = dict(self.LOGIC_CHOICES)

        for i, c in enumerate(self.conditionals or []):
            did = c.get("device_id")
            metric = c.get("metric", "")
            operator = c.get("operator", "")
            logic = c.get("logic")

            result.append({
                "index": i + 1,
                "device": devices_map.get(did),
                "metric": metric,
                "metric_display": metric_labels.get(metric, metric),
                "operator": operator,
                "operator_display": operator_labels.get(operator, operator),
                "threshold": c.get("threshold"),
                "duration_sec": c.get("duration_sec"),
                "logic": logic,
                "logic_display": logic_labels.get(logic, "") if logic else "",
            })

        return result


class Alert(models.Model):
    """Alerta generada por una regla."""

    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Advertencia"),
        ("critical", "Crítica"),
    ]
    STATUS_CHOICES = [
        ("activa", "Activa"),
        ("reconocida", "Reconocida"),
        ("resuelta", "Resuelta"),
    ]

    device = models.ForeignKey(
        "inventario.Device", on_delete=models.SET_NULL,
        null=True, blank=True, db_column="device_id",
        related_name="alerts",
    )
    interface = models.ForeignKey(
        "inventario.Interface", on_delete=models.SET_NULL,
        null=True, blank=True, db_column="interface_id",
        related_name="alerts",
    )
    rule = models.ForeignKey(
        AlertRule, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="alerts",
    )
    alert_type = models.CharField(max_length=50)
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES, default="warning",
    )
    message = models.TextField()
    value_observed = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True,
    )
    threshold_value = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="activa",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alerts"
        ordering = ["-created_at"]
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"

    def __str__(self):
        return f"[{self.severity}] {self.alert_type} - {self.device or 'N/A'}"


class Threshold(models.Model):
    """Umbral legacy (mantenido por compatibilidad)."""
    device = models.ForeignKey(
        "inventario.Device", on_delete=models.CASCADE,
        null=True, blank=True, db_column="device_id",
    )
    metric = models.CharField(max_length=50)
    warning_value = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True,
    )
    critical_value = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True,
    )
    duration_sec = models.PositiveIntegerField(default=60)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "thresholds"
        unique_together = [("device", "metric")]
        verbose_name = "Umbral (legacy)"
        verbose_name_plural = "Umbrales (legacy)"