# inventario/forms.py
"""
Formularios de la app `inventario`.

Incluye:
  - DeviceForm:      crear/editar equipos de red.
  - DeviceModelForm: crear/editar modelos de equipos con sus OIDs SNMP.

Los OIDs del modelo se exponen como campos individuales por clave
conocida (cpu_pct, mem_pct, mem_used, mem_size, mem_free, temp_c,
uptime) en lugar de un textarea JSON crudo. Esto evita errores de
sintaxis y hace la UI mucho más amigable.
"""
import re

from django import forms
from .models import Device, DeviceModel


# ============================================================
# PATRÓN DE VALIDACIÓN DE OID
# ============================================================
# Un OID SNMP es una secuencia de números separados por puntos.
# Ej: 1.3.6.1.2.1.1.3.0
OID_PATTERN = re.compile(r"^[0-9]+(\.[0-9]+)+$")

# Claves de OIDs conocidas por el servicio de chasis (chassis_oids.py).
# Solo estas se muestran como campos en el formulario.
OID_KEYS = [
    "cpu_pct",
    "mem_pct",
    "mem_used",
    "mem_size",
    "mem_free",
    "temp_c",
    "uptime",
]


# ============================================================
# HELPER: VALIDACIÓN DE OID
# ============================================================
def _validate_oid(value: str) -> str:
    """
    Valida el formato de un OID SNMP.

    Args:
        value: cadena a validar (puede venir vacía).

    Returns:
        str: el OID limpio (sin espacios) o cadena vacía.

    Raises:
        forms.ValidationError: si el formato no es válido.
    """
    if not value:
        return ""
    value = value.strip()
    if not value:
        return ""
    if not OID_PATTERN.match(value):
        raise forms.ValidationError(
            "El OID debe ser numérico con al menos un punto "
            "(ej: 1.3.6.1.2.1.1.3.0)."
        )
    return value


# ============================================================
# FORM: EQUIPO (ya existente)
# ============================================================
class DeviceForm(forms.ModelForm):
    """
    Formulario para crear o editar un equipo de red.

    Gestiona el filtrado dinámico de modelos según el fabricante
    seleccionado, la validación de IP única y la coherencia entre
    fabricante y modelo.
    """

    class Meta:
        model = Device
        fields = [
            "name", "ip",
            "device_type", "device_role",
            "vendor", "device_model",
            "location",
            "snmp_version", "snmp_community",
            "snmp_user", "snmp_auth", "snmp_priv",
            "tcp_ports", "active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "autofocus": True,
                "placeholder": "Ej: RB Güigüe",
            }),
            "ip": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "192.168.1.1",
            }),
            "device_type": forms.Select(attrs={"class": "form-select"}),
            "device_role": forms.Select(attrs={"class": "form-select"}),
            "vendor": forms.Select(attrs={
                "class": "form-select",
                "id": "id_vendor",
            }),
            "device_model": forms.Select(attrs={
                "class": "form-select",
                "id": "id_device_model",
            }),
            "location": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Güigüe",
            }),
            "snmp_version": forms.Select(
                choices=[("1", "SNMPv1"), ("2c", "SNMPv2c"), ("3", "SNMPv3")],
                attrs={"class": "form-select"},
            ),
            "snmp_community": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "public",
            }),
            "snmp_user": forms.TextInput(attrs={"class": "form-control"}),
            "snmp_auth": forms.TextInput(attrs={"class": "form-control"}),
            "snmp_priv": forms.TextInput(attrs={"class": "form-control"}),
            "tcp_ports": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "161,22,80",
            }),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Device model: requerido, con queryset inicial vacío
        self.fields["device_model"].required = True
        self.fields["device_model"].empty_label = "— Seleccione primero un fabricante —"
        self.fields["device_model"].queryset = DeviceModel.objects.none()

        # Determinar el vendor actual (POST > instance)
        vendor = None
        if self.data.get("vendor"):
            vendor = self.data.get("vendor")
        elif self.instance and self.instance.pk:
            vendor = self.instance.vendor

        if vendor:
            self.fields["device_model"].queryset = DeviceModel.objects.filter(
                vendor=vendor, active=True
            ).order_by("name")

    def clean_ip(self):
        """Valida que la IP sea única entre equipos."""
        ip = self.cleaned_data.get("ip", "").strip()
        qs = Device.objects.filter(ip=ip)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un equipo con esta IP.")
        return ip

    def clean(self):
        """Valida coherencia fabricante ↔ modelo y campos SNMPv3."""
        cleaned = super().clean()

        vendor = cleaned.get("vendor")
        device_model = cleaned.get("device_model")

        # Validar coherencia fabricante ↔ modelo
        if vendor and device_model:
            if device_model.vendor != vendor:
                self.add_error(
                    "device_model",
                    "El modelo seleccionado no pertenece al fabricante elegido.",
                )

        # Validar SNMPv3
        snmp_ver = cleaned.get("snmp_version")
        if snmp_ver == "3":
            if not cleaned.get("snmp_user"):
                self.add_error("snmp_user", "Requerido para SNMPv3.")
            if not cleaned.get("snmp_auth"):
                self.add_error("snmp_auth", "Requerido para SNMPv3.")

        return cleaned


# ============================================================
# FORM: MODELO DE EQUIPO (nuevo)
# ============================================================
class DeviceModelForm(forms.ModelForm):
    """
    Formulario para crear o editar un modelo de equipo.

    Los OIDs específicos del modelo se editan como **campos individuales
    por clave conocida** (cpu_pct, mem_pct, mem_used, mem_size, mem_free,
    temp_c, uptime), en lugar de exponer un textarea JSON crudo. Al
    guardar, se reconstruye el diccionario y se asigna al campo JSON
    `oids` del modelo.

    Reglas de negocio:
      - Si el modelo ya tiene equipos asociados, NO se permite cambiar
        el fabricante (rompería la consistencia Device.vendor ==
        DeviceModel.vendor).
      - Los OIDs son todos opcionales. Si se dejan vacíos, el poller
        de chasis usará los OIDs por defecto del fabricante
        (`chassis_oids.py`).
    """

    # --- Campos auxiliares para cada OID ---
    oid_cpu_pct = forms.CharField(
        required=False,
        label="CPU (%)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.14988.1.1.3.10.0",
        }),
        help_text="OID del porcentaje de uso de CPU.",
    )
    oid_mem_pct = forms.CharField(
        required=False,
        label="Memoria (%)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.7.1",
        }),
        help_text="OID del porcentaje de uso de memoria (si existe directo).",
    )
    oid_mem_used = forms.CharField(
        required=False,
        label="Memoria usada",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.2.1.25.2.3.1.6.65536",
        }),
        help_text="OID de bytes usados (se combina con mem_size).",
    )
    oid_mem_size = forms.CharField(
        required=False,
        label="Memoria total",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.2.1.25.2.3.1.5.65536",
        }),
        help_text="OID del tamaño total de memoria.",
    )
    oid_mem_free = forms.CharField(
        required=False,
        label="Memoria libre",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.9.9.48.1.1.1.6.1",
        }),
        help_text="OID de bytes libres (alternativa a mem_used + mem_size).",
    )
    oid_temp_c = forms.CharField(
        required=False,
        label="Temperatura (°C)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.14988.1.1.3.100.1.3.14",
        }),
        help_text="OID de temperatura del chasis.",
    )
    oid_uptime = forms.CharField(
        required=False,
        label="Uptime",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.2.1.1.3.0",
        }),
        help_text="OID de uptime (TimeTicks). Se autocompleta si se deja vacío.",
    )

    class Meta:
        model = DeviceModel
        fields = [
            "vendor",
            "name",
            "description",
            "is_wireless_link",
            "active",
        ]
        widgets = {
            "vendor": forms.Select(attrs={
                "class": "form-select",
                "autofocus": True,
            }),
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: RB4011iGS+, AirMax LiteBeam M5",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Notas opcionales sobre el modelo (firmware, características, etc.)",
            }),
            "is_wireless_link": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "vendor": "Fabricante",
            "name": "Nombre del modelo",
            "description": "Descripción",
            "is_wireless_link": "Es radio-enlace",
            "active": "Modelo activo",
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario.

        - Precarga los valores actuales de OIDs en sus campos
          correspondientes (si es edición).
        - Bloquea el campo `vendor` si el modelo ya tiene equipos
          asociados (para evitar inconsistencias).
        """
        super().__init__(*args, **kwargs)

        # Precargar OIDs existentes
        if self.instance and self.instance.pk and self.instance.oids:
            for key in OID_KEYS:
                field_name = f"oid_{key}"
                if field_name in self.fields:
                    value = self.instance.oids.get(key, "")
                    if value:
                        self.fields[field_name].initial = value

        # Bloquear cambio de vendor si hay equipos asociados
        if self.instance and self.instance.pk:
            has_devices = self.instance.devices.exists()
            if has_devices:
                self.fields["vendor"].disabled = True
                self.fields["vendor"].help_text = (
                    "No puedes cambiar el fabricante: este modelo ya está "
                    "siendo usado por uno o más equipos."
                )

    # ------------------------------------------------------------
    # VALIDACIÓN INDIVIDUAL DE CADA OID
    # ------------------------------------------------------------
    def clean_oid_cpu_pct(self):
        return _validate_oid(self.cleaned_data.get("oid_cpu_pct"))

    def clean_oid_mem_pct(self):
        return _validate_oid(self.cleaned_data.get("oid_mem_pct"))

    def clean_oid_mem_used(self):
        return _validate_oid(self.cleaned_data.get("oid_mem_used"))

    def clean_oid_mem_size(self):
        return _validate_oid(self.cleaned_data.get("oid_mem_size"))

    def clean_oid_mem_free(self):
        return _validate_oid(self.cleaned_data.get("oid_mem_free"))

    def clean_oid_temp_c(self):
        return _validate_oid(self.cleaned_data.get("oid_temp_c"))

    def clean_oid_uptime(self):
        return _validate_oid(self.cleaned_data.get("oid_uptime"))

    # ------------------------------------------------------------
    # VALIDACIÓN CRUZADA
    # ------------------------------------------------------------
    def clean_vendor(self):
        """
        Bloquea el cambio de fabricante si el modelo ya tiene equipos.

        El `disabled=True` en `__init__` ya lo impide en la UI, pero
        esta validación es la red de seguridad del lado servidor.
        """
        vendor = self.cleaned_data.get("vendor")
        if (
            self.instance
            and self.instance.pk
            and self.instance.devices.exists()
            and vendor != self.instance.vendor
        ):
            raise forms.ValidationError(
                "No puedes cambiar el fabricante de un modelo que ya está "
                "siendo usado por equipos. Desasócialos primero o crea un "
                "modelo nuevo."
            )
        return vendor

    def clean(self):
        """
        Valida coherencia entre campos de memoria.

        Si el usuario ingresa `mem_pct` Y también `mem_used`/`mem_size`,
        se prioriza `mem_pct` en el poller. No es un error, solo se
        advierte en la UI.
        """
        cleaned = super().clean()
        return cleaned

    # ------------------------------------------------------------
    # GUARDADO
    # ------------------------------------------------------------
    def save(self, commit=True):
        """
        Guarda el modelo, reconstruyendo el dict `oids` a partir de
        los campos auxiliares.

        Si todos los campos de OIDs están vacíos, `oids` queda como
        `{}` (diccionario vacío), lo que activa el fallback a los
        OIDs por defecto del fabricante.
        """
        instance = super().save(commit=False)

        # Reconstruir dict de OIDs solo con los campos no vacíos
        oids = {}
        for key in OID_KEYS:
            value = self.cleaned_data.get(f"oid_{key}")
            if value:
                oids[key] = value

        instance.oids = oids

        if commit:
            instance.save()
        return instance