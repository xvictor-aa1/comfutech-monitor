# core/views.py
"""Vista principal del dashboard."""
import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from alertas.models import Alert
from inventario.models import Device, Interface

log = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """
    Vista principal del dashboard.

    Muestra:
      - Métricas generales (equipos, interfaces, alertas).
      - Lista de equipos activos con estado en vivo.
      - Alertas recientes de los últimos 7 días.
    """
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    total_devices = Device.objects.filter(active=True).count()
    core_devices = Device.objects.filter(
        active=True, device_role__in=["core", "distribution"]
    ).count()
    total_interfaces = Interface.objects.filter(device__active=True).count()
    monitored_interfaces = Interface.objects.filter(
        device__active=True, monitored=True
    ).count()

    active_alerts = Alert.objects.filter(status="activa")
    critical_count = active_alerts.filter(severity="critical").count()
    warning_count = active_alerts.filter(severity="warning").count()

    recent_alerts = Alert.objects.filter(
        created_at__gte=last_7d
    ).select_related("device", "rule").order_by("-created_at")[:8]

    alerts_24h = Alert.objects.filter(created_at__gte=last_24h).count()

    context = {
        "total_devices": total_devices,
        "core_devices": core_devices,
        "total_interfaces": total_interfaces,
        "monitored_interfaces": monitored_interfaces,
        "active_alerts_count": active_alerts.count(),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "alerts_24h": alerts_24h,
        "recent_alerts": recent_alerts,
    }
    return render(request, "core/dashboard.html", context)