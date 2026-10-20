# alertas/admin.py
from django.contrib import admin
from django.utils import timezone
from .models import Alert, Threshold


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        "id", "severity", "alert_type", "device",
        "value_observed", "status", "created_at",
    )
    list_filter = ("severity", "status", "alert_type", "created_at")
    search_fields = ("message", "device__name", "alert_type")
    list_display_links = ("id", "severity")
    readonly_fields = ("created_at", "resolved_at")
    raw_id_fields = ("device", "interface")
    date_hierarchy = "created_at"
    actions = ["mark_resolved", "mark_acknowledged"]

    fieldsets = (
        ("Información", {
            "fields": ("device", "interface", "alert_type", "severity")
        }),
        ("Detalle", {
            "fields": ("message", "value_observed", "threshold_value")
        }),
        ("Estado", {
            "fields": ("status", "created_at", "resolved_at")
        }),
    )

    @admin.action(description="Marcar como resueltas")
    def mark_resolved(self, request, queryset):
        updated = queryset.filter(status__in=["activa", "reconocida"]).update(
            status="resuelta",
            resolved_at=timezone.now()
        )
        self.message_user(request, f"{updated} alerta(s) marcada(s) como resueltas.")

    @admin.action(description="Marcar como reconocidas")
    def mark_acknowledged(self, request, queryset):
        updated = queryset.filter(status="activa").update(status="reconocida")
        self.message_user(request, f"{updated} alerta(s) marcada(s) como reconocidas.")


@admin.register(Threshold)
class ThresholdAdmin(admin.ModelAdmin):
    list_display = (
        "id", "device", "metric", "warning_value",
        "critical_value", "duration_sec", "active",
    )
    list_filter = ("metric", "active")
    search_fields = ("device__name", "metric")
    list_editable = ("warning_value", "critical_value", "active")
    raw_id_fields = ("device",)

    fieldsets = (
        ("Alcance", {
            "fields": ("device", "metric"),
            "description": "Si no se selecciona dispositivo, el umbral aplica a todos."
        }),
        ("Valores", {
            "fields": ("warning_value", "critical_value", "duration_sec")
        }),
        ("Estado", {
            "fields": ("active",)
        }),
    )
