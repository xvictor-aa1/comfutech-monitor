# inventario/urls.py
"""
Rutas URL de la app `inventario`.

Incluye:
  - Equipos (Device): lista, detalle, crear, editar, eliminar,
    gestionar interfaces.
  - Modelos de equipo (DeviceModel): lista, crear, editar, eliminar,
    toggle activo/inactivo.
  - API: modelos filtrados por fabricante.
"""
from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    # ============================================================
    # EQUIPOS
    # ============================================================
    path("", views.device_list, name="device_list"),
    path("nuevo/", views.device_create, name="device_create"),
    path("api/models/", views.api_models, name="api_models"),
    path("<int:device_id>/", views.device_detail, name="device_detail"),
    path("<int:device_id>/editar/", views.device_edit, name="device_edit"),
    path("<int:device_id>/eliminar/", views.device_delete, name="device_delete"),
    path("<int:device_id>/interfaces/", views.device_interfaces, name="device_interfaces"),

    # ============================================================
    # MODELOS DE EQUIPO
    # ============================================================
    path("modelos/", views.device_model_list, name="device_model_list"),
    path("modelos/nuevo/", views.device_model_create, name="device_model_create"),
    path("modelos/<int:model_id>/editar/", views.device_model_edit, name="device_model_edit"),
    path("modelos/<int:model_id>/eliminar/", views.device_model_delete, name="device_model_delete"),
    path("modelos/<int:model_id>/toggle/", views.device_model_toggle, name="device_model_toggle"),
]