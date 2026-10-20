"""
URL configuration for sistema project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from core.views_auth import CustomLoginView

urlpatterns = [
    # Autenticación
    path("accounts/login/", CustomLoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    # Apps
    path("", include("core.urls")),
    path("equipos/", include("inventario.urls")),
    path("alertas/", include("alertas.urls")),
    path("monitoreo/", include("monitoreo.urls")),
]

# Admin de Django: solo accesible si DEBUG=True Y el usuario es superuser
# (queda como "puerta trasera" para emergencias en desarrollo)
if settings.DEBUG:
    urlpatterns += [path("django-admin/", admin.site.urls)]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
