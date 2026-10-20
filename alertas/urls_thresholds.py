from django.urls import path
from . import views

app_name = "thresholds"

urlpatterns = [
    path("", views.threshold_list, name="threshold_list"),
    path("nuevo/", views.threshold_create, name="threshold_create"),
    path("<int:threshold_id>/editar/", views.threshold_edit, name="threshold_edit"),
    path("<int:threshold_id>/eliminar/", views.threshold_delete, name="threshold_delete"),
]
