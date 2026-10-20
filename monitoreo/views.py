# monitoreo/views.py
"""
Vistas de la app `monitoreo`.

Incluye:
  - run_discovery: ejecuta discovery para un equipo.
  - run_discovery_all: ejecuta discovery para todos los equipos.
  - discovery_history: historial de ejecuciones por equipo.
  - monitor_status: estado del monitor (servicio + configuración).
  - monitor_live: monitoreo en vivo de equipos.
  - monitor_devices_live: API JSON de métricas en vivo.
"""
import logging
import time
import traceback

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.decorators import require_admin_or_super
from core.models import SystemConfig
from core.sorting import apply_sort, has_active_filters
from inventario.models import Device, DeviceModel
from .models import DiscoveryJob, MonitorStatus
from .services.chassis_oids import (
    get_available_health_metrics,
    has_meaningful_health_metrics,
)
from .services.discovery import discover_interfaces

log = logging.getLogger(__name__)


# ============================================================
# DISCOVERY — EQUIPO INDIVIDUAL
# ============================================================
@login_required
@require_admin_or_super()
def run_discovery(request, device_id):
    """Ejecuta el discovery SNMP para un equipo específico."""
    device = get_object_or_404(Device, pk=device_id)

    if request.method != "POST":
        return redirect("inventario:device_interfaces", device_id=device_id)

    # Crear job en estado running
    job = DiscoveryJob.objects.create(
        device=device,
        status="running",
        triggered_by=request.user if request.user.is_authenticated else None,
    )

    start = time.time()
    result = discover_interfaces(device)
    elapsed_ms = int((time.time() - start) * 1000)

    # Actualizar job
    job.finished_at = timezone.now()
    job.duration_ms = elapsed_ms
    job.interfaces_found = result["interfaces_found"]
    job.interfaces_up = result["interfaces_up"]
    job.interfaces_created = result["created"]
    job.interfaces_updated = result["updated"]
    job.interfaces_deleted = result["deleted"]

    if result["success"]:
        job.status = "success"
        messages.success(
            request,
            f"Discovery de '{device.name}': "
            f"{result['interfaces_found']} interfaces detectadas "
            f"({result['interfaces_up']} up), "
            f"{result['created']} nuevas, {result['updated']} actualizadas, "
            f"{result['deleted']} eliminadas. "
            f"Duración: {elapsed_ms} ms."
        )
    else:
        job.status = "failed"
        job.error_message = result.get("error") or "Error desconocido"
        messages.error(
            request,
            f"Discovery de '{device.name}' falló: {job.error_message}"
        )

    job.save()
    return redirect("inventario:device_interfaces", device_id=device_id)


# ============================================================
# DISCOVERY — TODOS LOS EQUIPOS
# ============================================================
@login_required
@require_admin_or_super()
def run_discovery_all(request):
    """Ejecuta el discovery en todos los equipos activos (endpoint JSON)."""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    devices = Device.objects.filter(active=True)
    total = devices.count()
    results = []

    for device in devices:
        job = DiscoveryJob.objects.create(
            device=device, status="running",
            triggered_by=request.user,
        )
        start = time.time()
        result = discover_interfaces(device)
        elapsed_ms = int((time.time() - start) * 1000)

        job.finished_at = timezone.now()
        job.duration_ms = elapsed_ms
        job.interfaces_found = result["interfaces_found"]
        job.interfaces_up = result["interfaces_up"]
        job.interfaces_created = result["created"]
        job.interfaces_updated = result["updated"]
        job.interfaces_deleted = result["deleted"]
        job.status = "success" if result["success"] else "failed"
        if not result["success"]:
            job.error_message = result.get("error") or "Error desconocido"
        job.save()

        results.append({
            "device": device.name,
            "success": result["success"],
            "found": result["interfaces_found"],
            "created": result["created"],
            "updated": result["updated"],
            "deleted": result["deleted"],
            "duration_ms": elapsed_ms,
            "error": result.get("error"),
        })

    return JsonResponse({
        "total": total,
        "results": results,
        "success_count": sum(1 for r in results if r["success"]),
        "failed_count": sum(1 for r in results if not r["success"]),
    })


# ============================================================
# DISCOVERY — HISTORIAL
# ============================================================
@login_required
def discovery_history(request, device_id):
    """Muestra el historial de ejecuciones del discovery de un equipo."""
    device = get_object_or_404(Device, pk=device_id)
    jobs = DiscoveryJob.objects.filter(device=device).select_related("triggered_by")

    # Filtros
    status_filter = request.GET.get("status", "")
    triggered_filter = request.GET.get("triggered_by", "")
    search = request.GET.get("q", "").strip()
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if status_filter:
        jobs = jobs.filter(status=status_filter)
    if triggered_filter:
        jobs = jobs.filter(triggered_by_id=triggered_filter)
    if search:
        jobs = jobs.filter(error_message__icontains=search)
    if date_from:
        jobs = jobs.filter(started_at__date__gte=date_from)
    if date_to:
        jobs = jobs.filter(started_at__date__lte=date_to)

    # Ordenamiento
    SORTABLE = {
        "fecha":        "started_at",
        "estado":       "status",
        "duracion":     "duration_ms",
        "encontradas":  "interfaces_found",
        "nuevas":       "interfaces_created",
        "actualizadas": "interfaces_updated",
        "eliminadas":   "interfaces_deleted",
        "disparado":    "triggered_by__username",
    }
    jobs, sort_key, order = apply_sort(request, jobs, SORTABLE, "-started_at")

    from django.contrib.auth.models import User
    user_ids = DiscoveryJob.objects.filter(device=device).values_list(
        "triggered_by", flat=True
    ).distinct()
    triggered_users = User.objects.filter(id__in=[u for u in user_ids if u])

    base = DiscoveryJob.objects.filter(device=device)
    context = {
        "device": device,
        "jobs": jobs[:200],
        "sort_key": sort_key,
        "order": order,
        "status_filter": status_filter,
        "triggered_filter": triggered_filter,
        "search": search,
        "date_from": date_from,
        "date_to": date_to,
        "triggered_users": triggered_users,
        "count_all": base.count(),
        "count_success": base.filter(status="success").count(),
        "count_failed": base.filter(status="failed").count(),
        "count_running": base.filter(status="running").count(),
        "has_filters": has_active_filters(
            request, ["status", "triggered_by", "q", "date_from", "date_to"]
        ),
    }
    return render(request, "monitoreo/discovery_history.html", context)


# ============================================================
# MONITOR — ESTADO DEL SERVICIO
# ============================================================
@login_required
def monitor_status(request):
    """
    Vista principal del monitor: estado del servicio + configuración.

    Muestra:
      - Estado (activo/detenido) del proceso monitor.
      - Último heartbeat, host y PID.
      - Intervalos configurados de cada poller.
      - Última ejecución de cada poller.
    """
    status = MonitorStatus.objects.filter(id=1).first()
    cfg = SystemConfig.get()

    context = {
        "status": status,
        "is_alive": status.is_alive if status else False,
        "cfg": cfg,
        "monitor_enabled": cfg.monitor_enabled,
        "snmp_interval": cfg.snmp_poll_interval,
        "health_interval": cfg.health_poll_interval,
        "icmp_interval": cfg.icmp_poll_interval,
    }
    return render(request, "monitoreo/monitor_status.html", context)


# ============================================================
# MONITOR — LIVE (MONITOREO EN VIVO)
# ============================================================
@login_required
def monitor_live(request):
    """
    Página de Monitoreo en vivo.

    Muestra las tarjetas con los últimos valores reportados por los
    pollers: ICMP, SNMP tráfico, Core Health y estado TCP.

    Solo renderiza el template; los datos los pide el frontend
    vía AJAX a `monitor_devices_live`.
    """
    
    # Equipos con sus modelos precargados
    devices = (
        Device.objects
        .filter(active=True)
        .select_related("device_model")
        .prefetch_related("interfaces")
    )

    # Estadísticas para el header
    total_devices = devices.count()
    monitored_count = sum(
        1 for d in devices if any(i.monitored for i in d.interfaces.all())
    )

    context = {
        "devices_count": total_devices,
        "monitored_count": monitored_count,
    }
    return render(request, "monitoreo/monitor_live.html", context)


# ============================================================
# MONITOR — API JSON LIVE
# ============================================================
@login_required
def monitor_devices_live(request):
    """
    API JSON con los últimos valores de cada equipo.

    Características:
      - Devuelve `has_health_metrics` (bool) y `available_health_metrics`
        (list) para que el frontend decida si mostrar Core Health.
      - Devuelve `is_wireless_link` (bool) y `wireless_info` (dict) con
        la utilización y capacidad del radioenlace.
      - Errores de InfluxDB devuelven listas vacías en lugar de 500.
      - Incluye un bloque `_debug` con contadores para diagnóstico.

    Returns:
        JsonResponse: {timestamp, devices: [...], _debug: {...}}
    """
    from .services import influx_reader

    try:
        # --- Equipos activos con modelo y interfaces precargadas ---
        devices = list(
            Device.objects
            .filter(active=True)
            .select_related("device_model")
            .prefetch_related("interfaces")
        )

        # --- Snapshot de métricas (con caché interna) ---
        snapshot = influx_reader.get_live_snapshot()
        icmp_data = snapshot.get("icmp", {})
        traffic_data = snapshot.get("traffic", {})
        health_data = snapshot.get("health", {})
        tcp_data = snapshot.get("tcp", {})

        # --- Mapa de alias por dispositivo ---
        alias_map = {}
        for device in devices:
            alias_map[device.id] = {
                i.if_name: (i.if_alias or "")
                for i in device.interfaces.all() if i.if_name
            }

        result = []
        for device in devices:
            monitored_ifaces = [i for i in device.interfaces.all() if i.monitored]

            # --- Determinar si es radio-enlace ---
            is_wireless = bool(
                device.device_model and device.device_model.is_wireless_link
            )

            # --- Métricas de chasis disponibles para este equipo ---
            available_health = get_available_health_metrics(device)
            has_health = has_meaningful_health_metrics(device)

            # --- ICMP ---
            icmp = icmp_data.get(device.name, {})
            icmp_payload = None
            if icmp:
                icmp_payload = {
                    "alive": icmp.get("alive"),
                    "rtt": icmp.get("rtt"),
                    "loss": icmp.get("loss"),
                    "ts": icmp.get("ts").isoformat() if icmp.get("ts") else None,
                }

            # --- Tráfico ---
            traffic_payload = []
            if device.name in traffic_data:
                for t in traffic_data[device.name]:
                    iface_name = t.get("interface")
                    alias = alias_map.get(device.id, {}).get(iface_name, "")
                    traffic_payload.append({
                        "interface": iface_name,
                        "alias": alias,
                        "in_bps": t.get("in_bps"),
                        "out_bps": t.get("out_bps"),
                        "utilization": t.get("utilization_pct"),
                        "capacity_bps": t.get("capacity_bps"),
                        "ts": t.get("ts").isoformat() if t.get("ts") else None,
                    })

            # --- Información extra para radioenlaces ---
            # Se busca la interfaz con la mayor utilización para destacarla
            wireless_info = None
            if is_wireless and traffic_payload:
                valid_traffic = [
                    t for t in traffic_payload
                    if t.get("utilization") is not None
                ]
                if valid_traffic:
                    best = max(valid_traffic, key=lambda t: t["utilization"])
                    wireless_info = {
                        "interface": best.get("interface"),
                        "alias": best.get("alias"),
                        "capacity_bps": best.get("capacity_bps"),
                        "utilization_pct": best.get("utilization"),
                        "in_bps": best.get("in_bps"),
                        "out_bps": best.get("out_bps"),
                    }

            # --- Chasis ---
            health = health_data.get(device.name, {})
            health_payload = None
            if health:
                health_payload = {
                    "cpu": health.get("cpu"),
                    "mem": health.get("mem"),
                    "temp": health.get("temp"),
                    "uptime": health.get("uptime"),
                    "ts": health.get("ts").isoformat() if health.get("ts") else None,
                }

            # --- TCP ---
            tcp_payload = []
            if device.name in tcp_data:
                for t in tcp_data[device.name]:
                    tcp_payload.append({
                        "port": t.get("port"),
                        "is_open": t.get("is_open"),
                    })

            result.append({
                "id": device.id,
                "name": device.name,
                "ip": device.ip,
                "role": device.device_role,
                "vendor": device.vendor,
                "model": device.device_model.name if device.device_model else None,
                "location": device.location,
                "has_traffic": bool(monitored_ifaces),
                # Flags nuevos:
                "has_health_metrics": has_health,
                "available_health_metrics": available_health,
                "is_wireless_link": is_wireless,
                "wireless_info": wireless_info,
                # Payloads:
                "icmp": icmp_payload,
                "traffic": traffic_payload,
                "health": health_payload,
                "tcp": tcp_payload,
            })

        return JsonResponse({
            "timestamp": timezone.now().isoformat(),
            "devices": result,
            "_debug": {
                "count_devices": len(result),
                "count_icmp": len(icmp_data),
                "count_traffic": len(traffic_data),
                "count_health": len(health_data),
                "count_tcp": len(tcp_data),
                "client_ip": request.META.get("REMOTE_ADDR"),
                "forwarded_for": request.META.get("HTTP_X_FORWARDED_FOR"),
            },
        })

    except Exception as e:
        log.exception("Error en monitor_devices_live: %s", e)
        return JsonResponse({
            "timestamp": timezone.now().isoformat(),
            "devices": [],
            "error": str(e),
            "traceback": traceback.format_exc() if settings.DEBUG else None,
        }, status=500)