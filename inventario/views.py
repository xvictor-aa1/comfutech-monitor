# inventario/views.py
"""
Vistas de la app `inventario`.

Incluye:
  - Equipos (Device):
      · device_list     — listado paginado (10/pág) con filtros y orden.
      · device_detail   — detalle de un equipo.
      · device_create   — crear equipo.
      · device_edit     — editar equipo.
      · device_delete   — eliminar equipo.
      · device_interfaces — gestionar interfaces (marcar monitored).
      · api_models      — API JSON de modelos por fabricante.

  - Modelos de equipo (DeviceModel) — NUEVO:
      · device_model_list   — listado paginado (10/pág).
      · device_model_create — crear modelo.
      · device_model_edit   — editar modelo.
      · device_model_delete — eliminar modelo (bloqueado si hay equipos).
      · device_model_toggle — activar/desactivar modelo.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import require_admin_or_super
from core.sorting import apply_sort, has_active_filters, ROLE_ORDER
from .forms import DeviceForm, DeviceModelForm
from .models import Device, DeviceModel, Interface


# ============================================================
# API: modelos filtrados por fabricante
# ============================================================
@login_required
def api_models(request):
    """
    Devuelve los modelos activos de un fabricante (JSON).

    Query params:
        vendor: nombre del fabricante (str).

    Returns:
        JsonResponse: {"models": [{"id": int, "name": str}, ...]}
    """
    vendor = request.GET.get("vendor", "").strip()
    if not vendor:
        return JsonResponse({"models": []})

    models = DeviceModel.objects.filter(
        vendor=vendor, active=True
    ).order_by("name").values("id", "name")

    return JsonResponse({"models": list(models)})


# ============================================================
# LISTA DE EQUIPOS (con paginación)
# ============================================================
@login_required
def device_list(request):
    """
    Lista los equipos con filtros, ordenamiento y **paginación (10/pág)**.

    Filtros aceptados vía GET:
        q       — búsqueda por nombre, IP o ubicación.
        role    — rol del equipo (core/distribution/access/cpe).
        vendor  — fabricante.
        model   — ID del modelo.
        active  — "1" activos, "0" inactivos.
    """
    q = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "")
    vendor_filter = request.GET.get("vendor", "")
    model_filter = request.GET.get("model", "")
    active_filter = request.GET.get("active", "")

    # Queryset base con anotaciones para evitar N+1
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

    # Aplicar filtros
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

    # Ordenamiento
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

    # Paginación: 10 equipos por página
    paginator = Paginator(devices, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # Fabricantes disponibles (para el filtro)
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
        "devices": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
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
# DETALLE DE EQUIPO
# ============================================================
@login_required
def device_detail(request, device_id):
    """
    Muestra el detalle de un equipo, sus interfaces y sus últimas alertas.
    """
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
# CREAR EQUIPO
# ============================================================
@login_required
@require_admin_or_super()
def device_create(request):
    """Crea un nuevo equipo."""
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
# EDITAR EQUIPO
# ============================================================
@login_required
@require_admin_or_super()
def device_edit(request, device_id):
    """Edita un equipo existente."""
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
# ELIMINAR EQUIPO
# ============================================================
@login_required
@require_admin_or_super()
def device_delete(request, device_id):
    """Elimina un equipo (con confirmación previa)."""
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
# GESTIONAR INTERFACES DE UN EQUIPO
# ============================================================
@login_required
def device_interfaces(request, device_id):
    """
    Permite marcar/desmarcar interfaces como monitoreadas.

    GET:  muestra la lista de interfaces con filtros y orden.
    POST: guarda el nuevo conjunto de interfaces monitoreadas.
    """
    device = get_object_or_404(Device, pk=device_id)
    interfaces = device.interfaces.all()

    if request.method == "POST":
        # Control de permisos: solo admin/superadmin puede modificar
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


# ============================================================
# MODELOS DE EQUIPO — LISTA PAGINADA
# ============================================================
@login_required
def device_model_list(request):
    """
    Lista los modelos de equipo con filtros, ordenamiento y **paginación**.

    Filtros aceptados vía GET:
        q        — búsqueda por nombre o descripción.
        vendor   — fabricante.
        wireless — "1" radio-enlaces, "0" no radio-enlaces.
        active   — "1" activos, "0" inactivos.

    Stats mostradas arriba de la tabla:
        count_all          — total de modelos.
        count_active       — modelos activos.
        count_wireless     — modelos marcados como radio-enlace.
        count_custom_oids  — modelos con al menos un OID propio.
    """
    q = request.GET.get("q", "").strip()
    vendor_filter = request.GET.get("vendor", "")
    wireless_filter = request.GET.get("wireless", "")
    active_filter = request.GET.get("active", "")

    # Queryset base con conteo de equipos asociados
    models_qs = DeviceModel.objects.annotate(
        devices_count=Count("devices", distinct=True),
        active_devices_count=Count(
            "devices",
            filter=Q(devices__active=True),
            distinct=True,
        ),
    )

    # Aplicar filtros
    if q:
        models_qs = models_qs.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )
    if vendor_filter:
        models_qs = models_qs.filter(vendor=vendor_filter)
    if wireless_filter == "1":
        models_qs = models_qs.filter(is_wireless_link=True)
    elif wireless_filter == "0":
        models_qs = models_qs.filter(is_wireless_link=False)
    if active_filter == "1":
        models_qs = models_qs.filter(active=True)
    elif active_filter == "0":
        models_qs = models_qs.filter(active=False)

    # Ordenamiento
    SORTABLE = {
        "fabricante":  "vendor",
        "modelo":      "name",
        "radio":       "is_wireless_link",
        "equipos":     "devices_count",
        "activo":      "active",
        "actualizado": "updated_at",
    }
    models_qs, sort_key, order = apply_sort(
        request, models_qs, SORTABLE, "vendor"
    )

    # Paginación: 10 modelos por página
    paginator = Paginator(models_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # Conteo de modelos con OIDs personalizados.
    # Se hace en Python porque `exclude(oids={})` no es portable
    # entre MySQL/PostgreSQL con JSONField.
    count_custom_oids = sum(
        1 for m in DeviceModel.objects.only("oids") if m.oids
    )

    context = {
        "models": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "q": q,
        "vendor_filter": vendor_filter,
        "wireless_filter": wireless_filter,
        "active_filter": active_filter,
        "sort_key": sort_key,
        "order": order,
        "vendor_choices": DeviceModel.VENDOR_CHOICES,
        "count_all": DeviceModel.objects.count(),
        "count_active": DeviceModel.objects.filter(active=True).count(),
        "count_wireless": DeviceModel.objects.filter(
            is_wireless_link=True
        ).count(),
        "count_custom_oids": count_custom_oids,
        "has_filters": has_active_filters(
            request, ["q", "vendor", "wireless", "active"]
        ),
    }
    return render(request, "inventario/device_model_list.html", context)


# ============================================================
# MODELOS DE EQUIPO — CREAR
# ============================================================
@login_required
@require_admin_or_super()
def device_model_create(request):
    """Crea un nuevo modelo de equipo con sus OIDs."""
    if request.method == "POST":
        form = DeviceModelForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(
                request,
                f"Modelo '{obj.name}' ({obj.vendor}) creado.",
            )
            return redirect("inventario:device_model_list")
    else:
        form = DeviceModelForm()

    return render(request, "inventario/device_model_form.html", {
        "form": form,
        "title": "Nuevo modelo de equipo",
        "is_edit": False,
        "devices_count": 0,
    })


# ============================================================
# MODELOS DE EQUIPO — EDITAR
# ============================================================
@login_required
@require_admin_or_super()
def device_model_edit(request, model_id):
    """
    Edita un modelo de equipo existente.

    Si el modelo ya tiene equipos asociados, el campo `vendor` se
    muestra deshabilitado (para no romper la coherencia con
    `Device.vendor`).
    """
    obj = get_object_or_404(DeviceModel, pk=model_id)

    if request.method == "POST":
        form = DeviceModelForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Modelo '{obj.name}' actualizado.")
            return redirect("inventario:device_model_list")
    else:
        form = DeviceModelForm(instance=obj)

    return render(request, "inventario/device_model_form.html", {
        "form": form,
        "model_obj": obj,
        "title": f"Editar: {obj.vendor} - {obj.name}",
        "is_edit": True,
        "devices_count": obj.devices.count(),
    })


# ============================================================
# MODELOS DE EQUIPO — ELIMINAR
# ============================================================
@login_required
@require_admin_or_super()
def device_model_delete(request, model_id):
    """
    Elimina un modelo (con confirmación).

    Regla de negocio: si hay equipos usando el modelo, **se bloquea**
    la eliminación. Se sugiere desactivarlo en su lugar (soft delete).
    """
    obj = get_object_or_404(DeviceModel, pk=model_id)
    devices_count = obj.devices.count()

    if request.method == "POST":
        if devices_count > 0:
            messages.error(
                request,
                f"No se puede eliminar: hay {devices_count} equipo(s) "
                "que usan este modelo. Desactívalo en su lugar.",
            )
            return redirect(
                "inventario:device_model_edit", model_id=obj.id
            )

        name = obj.name
        obj.delete()
        messages.success(request, f"Modelo '{name}' eliminado.")
        return redirect("inventario:device_model_list")

    return render(request, "inventario/device_model_confirm_delete.html", {
        "model_obj": obj,
        "devices_count": devices_count,
    })


# ============================================================
# MODELOS DE EQUIPO — TOGGLE ACTIVO/INACTIVO
# ============================================================
@login_required
@require_admin_or_super()
def device_model_toggle(request, model_id):
    """
    Activa o desactiva un modelo (POST).

    Es útil para retirar un modelo sin perderlo ni eliminar sus
    equipos asociados.
    """
    if request.method != "POST":
        return redirect("inventario:device_model_list")

    obj = get_object_or_404(DeviceModel, pk=model_id)
    obj.active = not obj.active
    obj.save(update_fields=["active", "updated_at"])

    state = "activado" if obj.active else "desactivado"
    messages.success(request, f"Modelo '{obj.name}' {state}.")
    return redirect(
        request.META.get("HTTP_REFERER", "inventario:device_model_list")
    )