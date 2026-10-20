# inventario/urls.py
from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.device_list, name="device_list"),
    path("nuevo/", views.device_create, name="device_create"),
    path("api/models/", views.api_models, name="api_models"),
    path("<int:device_id>/", views.device_detail, name="device_detail"),
    path("<int:device_id>/editar/", views.device_edit, name="device_edit"),
    path("<int:device_id>/eliminar/", views.device_delete, name="device_delete"),
    path("<int:device_id>/interfaces/", views.device_interfaces, name="device_interfaces"),
]
