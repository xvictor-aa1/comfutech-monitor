# inventario/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import require_admin_or_super
from core.sorting import apply_sort, has_active_filters, ROLE_ORDER
from .forms import DeviceForm
from .models import Device, DeviceModel, Interface


# ============================================================
# API: modelos filtrados por fabricante
# ============================================================
@login_required
def api_models(request):
    """Devuelve los modelos activos de un fabricante (JSON)."""
    vendor = request.GET.get("vendor", "").strip()
    if not vendor:
        return JsonResponse({"models": []})

    models = DeviceModel.objects.filter(
        vendor=vendor, active=True
    ).order_by("name").values("id", "name")

    return JsonResponse({"models": list(models)})


# ============================================================
# LISTA DE EQUIPOS
# ============================================================
@login_required
def device_list(request):
    q = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "")
    vendor_filter = request.GET.get("vendor", "")
    model_filter = request.GET.get("model", "")
    active_filter = request.GET.get("active", "")

    devices = (
        Device.objects
        .select_related("device_model")
        .prefetch_related("interfaces")
        .annotate(
            role_order=ROLE_ORDER,
            iface_count=Count("interfaces", distinct=True),
            monitored_count=Count(
                "interfaces",
                filter=Q(interfaces__monitored=True),
                distinct=True,
            ),
        )
    )

    if q:
        devices = devices.filter(
            Q(name__icontains=q)
            | Q(ip__icontains=q)
            | Q(location__icontains=q)
        )
    if role_filter:
        devices = devices.filter(device_role=role_filter)
    if vendor_filter:
        devices = devices.filter(vendor=vendor_filter)
    if model_filter:
        devices = devices.filter(device_model_id=model_filter)
    if active_filter == "1":
        devices = devices.filter(active=True)
    elif active_filter == "0":
        devices = devices.filter(active=False)

    SORTABLE = {
        "nombre":     "name",
        "ip":         "ip",
        "tipo":       "device_type",
        "rol":        "role_order",
        "vendor":     "vendor",
        "modelo":     "device_model__name",
        "ubicacion":  "location",
        "interfaces": "iface_count",
        "activo":     "active",
    }
    devices, sort_key, order = apply_sort(request, devices, SORTABLE, "name")

    # Fabricantes disponibles
    vendor_choices = (
        Device.objects
        .exclude(vendor__isnull=True)
        .exclude(vendor="")
        .values_list("vendor", flat=True)
        .distinct()
        .order_by("vendor")
    )

    # Modelos del fabricante seleccionado (si aplica)
    if vendor_filter:
        model_choices = DeviceModel.objects.filter(
            vendor=vendor_filter, active=True
        ).order_by("name")
    else:
        model_choices = DeviceModel.objects.none()

    context = {
        "devices": devices,
        "q": q,
        "role_filter": role_filter,
        "vendor_filter": vendor_filter,
        "model_filter": model_filter,
        "active_filter": active_filter,
        "sort_key": sort_key,
        "order": order,
        "role_choices": Device.ROLE_CHOICES,
        "vendor_choices": vendor_choices,
        "model_choices": model_choices,
        "count_all": Device.objects.count(),
        "count_active": Device.objects.filter(active=True).count(),
        "count_core": Device.objects.filter(
            active=True, device_role__in=["core", "distribution"]
        ).count(),
        "has_filters": has_active_filters(
            request, ["q", "role", "vendor", "model", "active"]
        ),
    }
    return render(request, "inventario/device_list.html", context)


# ============================================================
# DETALLE
# ============================================================
@login_required
def device_detail(request, device_id):
    device = get_object_or_404(
        Device.objects.select_related("device_model"), pk=device_id
    )
    interfaces = device.interfaces.all().order_by("if_index")
    monitored = interfaces.filter(monitored=True)
    alerts = device.alerts.order_by("-created_at")[:10]

    context = {
        "device": device,
        "interfaces": interfaces,
        "monitored_count": monitored.count(),
        "total_count": interfaces.count(),
        "alerts": alerts,
    }
    return render(request, "inventario/device_detail.html", context)


# ============================================================
# CREAR
# ============================================================
@login_required
@require_admin_or_super()
def device_create(request):
    if request.method == "POST":
        form = DeviceForm(request.POST)
        if form.is_valid():
            d = form.save()
            messages.success(request, f"Equipo '{d.name}' creado.")
            return redirect("inventario:device_detail", device_id=d.id)
    else:
        form = DeviceForm()

    return render(request, "inventario/device_form.html", {
        "form": form,
        "title": "Nuevo equipo",
        "is_edit": False,
    })


# ============================================================
# EDITAR
# ============================================================
@login_required
@require_admin_or_super()
def device_edit(request, device_id):
    device = get_object_or_404(Device, pk=device_id)

    if request.method == "POST":
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            form.save()
            messages.success(request, f"Equipo '{device.name}' actualizado.")
            return redirect("inventario:device_detail", device_id=device.id)
    else:
        form = DeviceForm(instance=device)

    return render(request, "inventario/device_form.html", {
        "form": form,
        "device": device,
        "title": f"Editar: {device.name}",
        "is_edit": True,
    })


# ============================================================
# ELIMINAR
# ============================================================
@login_required
@require_admin_or_super()
def device_delete(request, device_id):
    device = get_object_or_404(Device, pk=device_id)

    if request.method == "POST":
        name = device.name
        device.delete()
        messages.success(request, f"Equipo '{name}' eliminado.")
        return redirect("inventario:device_list")

    return render(request, "inventario/device_confirm_delete.html", {
        "device": device,
    })


# ============================================================
# INTERFACES
# ============================================================
@login_required
def device_interfaces(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    interfaces = device.interfaces.all()

    if request.method == "POST":
        if not (
            request.user.is_superuser
            or request.user.groups.filter(name="Administrador").exists()
        ):
            raise PermissionDenied("No tienes permisos.")

        selected_ids = set(request.POST.getlist("monitored"))
        updated = 0

        for iface in interfaces:
            should = str(iface.id) in selected_ids
            if iface.monitored != should:
                iface.monitored = should
                iface.save()
                updated += 1

        if updated:
            messages.success(request, f"Se actualizaron {updated} interfaz(es).")
        else:
            messages.info(request, "No hubo cambios.")

        return redirect("inventario:device_interfaces", device_id=device_id)

    # Filtros
    search = request.GET.get("q", "").strip()
    monitored_filter = request.GET.get("monitored", "")
    status_filter = request.GET.get("status", "")
    type_filter = request.GET.get("type", "")
    has_speed_filter = request.GET.get("has_speed", "")

    if search:
        interfaces = interfaces.filter(
            Q(if_name__icontains=search) | Q(if_alias__icontains=search)
        )
    if monitored_filter == "1":
        interfaces = interfaces.filter(monitored=True)
    elif monitored_filter == "0":
        interfaces = interfaces.filter(monitored=False)
    if status_filter == "up":
        interfaces = interfaces.filter(oper_status=True)
    elif status_filter == "down":
        interfaces = interfaces.filter(oper_status=False)
    if type_filter:
        interfaces = interfaces.filter(if_type=type_filter)
    if has_speed_filter == "1":
        interfaces = interfaces.filter(if_speed_bps__gt=0)
    elif has_speed_filter == "0":
        interfaces = interfaces.filter(if_speed_bps=0)

    # Ordenamiento
    SORTABLE = {
        "index":     "if_index",
        "nombre":    "if_name",
        "alias":     "if_alias",
        "tipo":      "if_type",
        "velocidad": "if_speed_bps",
        "estado":    "oper_status",
        "monitor":   "monitored",
    }
    interfaces, sort_key, order = apply_sort(
        request, interfaces, SORTABLE, "if_index"
    )

    type_choices = list(
        device.interfaces.values_list("if_type", flat=True).distinct()
    )

    context = {
        "device": device,
        "interfaces": interfaces,
        "sort_key": sort_key,
        "order": order,
        "search": search,
        "monitored_filter": monitored_filter,
        "status_filter": status_filter,
        "type_filter": type_filter,
        "has_speed_filter": has_speed_filter,
        "type_choices": sorted([t for t in type_choices if t]),
        "count_all": device.interfaces.count(),
        "count_monitored": device.interfaces.filter(monitored=True).count(),
        "count_up": device.interfaces.filter(oper_status=True).count(),
        "has_filters": has_active_filters(
            request, ["q", "monitored", "status", "type", "has_speed"]
        ),
    }
    return render(request, "inventario/device_interfaces.html", context)
