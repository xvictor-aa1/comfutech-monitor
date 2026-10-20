# monitoreo/models.py
from django.conf import settings
from django.db import models


class DiscoveryJob(models.Model):
    """Registro de cada ejecución del discovery."""
    STATUS_CHOICES = [
        ("running", "En ejecución"),
        ("success", "Exitosa"),
        ("failed", "Fallida"),
    ]

    device = models.ForeignKey(
        "inventario.Device",
        on_delete=models.CASCADE,
        related_name="discovery_jobs",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="running"
    )

    interfaces_found = models.IntegerField(default=0)
    interfaces_up = models.IntegerField(default=0)
    interfaces_created = models.IntegerField(default=0)
    interfaces_updated = models.IntegerField(default=0)
    interfaces_deleted = models.IntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="discovery_jobs",
    )

    class Meta:
        db_table = "discovery_jobs"
        ordering = ["-started_at"]
        verbose_name = "Ejecución de Discovery"
        verbose_name_plural = "Ejecuciones de Discovery"

    def __str__(self):
        return (
            f"{self.device.name} - {self.get_status_display()} "
            f"- {self.started_at:%Y-%m-%d %H:%M}"
        )

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"


class MonitorStatus(models.Model):
    """
    Estado del monitor en background. Solo hay una fila (id=1).
    """
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="stopped")
    hostname = models.CharField(max_length=100, blank=True)
    pid = models.IntegerField(null=True, blank=True)

    last_traffic_run = models.DateTimeField(null=True, blank=True)
    last_health_run = models.DateTimeField(null=True, blank=True)
    last_icmp_run = models.DateTimeField(null=True, blank=True)

    last_error = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "monitor_status"
        verbose_name = "Estado del Monitor"
        verbose_name_plural = "Estado del Monitor"

    def __str__(self):
        return f"Monitor {self.status} - {self.last_heartbeat or 'nunca'}"

    @property
    def is_alive(self) -> bool:
        """¿El monitor ha dado señal en los últimos 90 segundos?"""
        from django.utils import timezone
        if not self.last_heartbeat:
            return False
        age = (timezone.now() - self.last_heartbeat).total_seconds()
        return age < 90 and self.status == "running"