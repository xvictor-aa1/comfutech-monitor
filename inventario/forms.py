# inventario/forms.py
"""
Formularios de la app `inventario`.

Incluye:
  - DeviceForm:      crear/editar equipos de red.
  - DeviceModelForm: crear/editar modelos de equipos con OIDs SNMP
                     de chasis y de radiofrecuencia.

El formulario de modelos expone los OIDs como **campos individuales
por clave conocida** (CPU, memoria, temperatura, frecuencia, capacidad
RX/TX, señal, ruido, CCQ, etc.) para evitar errores de sintaxis JSON.
Además, incluye un **editor JSON opcional** para usuarios avanzados
que necesiten pegar configuraciones completas o definir claves no
listadas.
"""
import json
import re

from django import forms
from .models import Device, DeviceModel


# ============================================================
# PATRÓN DE VALIDACIÓN DE OID
# ============================================================
# Un OID SNMP es una secuencia de números separados por puntos.
# Ej: 1.3.6.1.2.1.1.3.0
OID_PATTERN = re.compile(r"^[0-9]+(\.[0-9]+)+$")

# Claves de OIDs de chasis (CPU, memoria, temperatura, uptime).
CHASSIS_OID_KEYS = [
    "cpu_pct",
    "mem_pct",
    "mem_used",
    "mem_size",
    "mem_free",
    "temp_c",
    "uptime",
]

# Claves de OIDs de radiofrecuencia (frecuencia, capacidad, señal, etc.).
RADIO_OID_KEYS = [
    "freq_mhz",
    "capacity_rx_kbps",
    "capacity_tx_kbps",
    "noise_dbm",
    "signal_dbm",
    "ccq_pct",
    "tx_rate_mbps",
    "rx_rate_mbps",
    "sta_count",
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
# FORM: EQUIPO (Device)
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
        """
        Inicializa el formulario.

        - Deja el queryset de `device_model` vacío hasta que se
          seleccione un fabricante (se llena vía AJAX).
        - Si el formulario ya tiene datos (POST) o una instancia,
          precarga los modelos del fabricante correspondiente.
        """
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
        """
        Valida que la IP sea única entre equipos.

        Returns:
            str: la IP limpia.

        Raises:
            forms.ValidationError: si ya existe otro equipo con esa IP.
        """
        ip = self.cleaned_data.get("ip", "").strip()
        qs = Device.objects.filter(ip=ip)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un equipo con esta IP.")
        return ip

    def clean(self):
        """
        Validaciones cruzadas del formulario.

        - Coherencia fabricante ↔ modelo.
        - Campos requeridos para SNMPv3.

        Returns:
            dict: cleaned_data con los ajustes aplicados.
        """
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
# FORM: MODELO DE EQUIPO (DeviceModel)
# ============================================================
class DeviceModelForm(forms.ModelForm):
    """
    Formulario para crear o editar un modelo de equipo.

    - Los OIDs se editan como campos individuales por clave conocida.
    - Se añade un campo `oids_json` para edición directa del JSON
      completo (opcional).
    - El campo `vendor` se bloquea si el modelo ya tiene equipos
      asociados.
    """

    # --- Campos de OIDs de chasis ---
    oid_cpu_pct = forms.CharField(
        required=False, label="CPU (%)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.14988.1.1.3.10.0",
        }),
        help_text="OID del porcentaje de uso de CPU.",
    )
    oid_mem_pct = forms.CharField(
        required=False, label="Memoria (%)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.7.1",
        }),
        help_text="OID del porcentaje de uso de memoria (si existe directo).",
    )
    oid_mem_used = forms.CharField(
        required=False, label="Memoria usada",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.2.1.25.2.3.1.6.65536",
        }),
        help_text="OID de bytes usados (se combina con mem_size).",
    )
    oid_mem_size = forms.CharField(
        required=False, label="Memoria total",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.2.1.25.2.3.1.5.65536",
        }),
        help_text="OID del tamaño total de memoria.",
    )
    oid_mem_free = forms.CharField(
        required=False, label="Memoria libre",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.9.9.48.1.1.1.6.1",
        }),
        help_text="OID de bytes libres (alternativa a mem_used + mem_size).",
    )
    oid_temp_c = forms.CharField(
        required=False, label="Temperatura (°C)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.14988.1.1.3.100.1.3.14",
        }),
        help_text="OID de temperatura del chasis.",
    )
    oid_uptime = forms.CharField(
        required=False, label="Uptime",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.2.1.1.3.0",
        }),
        help_text="OID de uptime (TimeTicks). Se autocompleta si se deja vacío.",
    )

    # --- Campos de OIDs de radiofrecuencia ---
    oid_freq_mhz = forms.CharField(
        required=False, label="Frecuencia (MHz)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.41112.1.4.1.1.4",
        }),
        help_text="Frecuencia de operación del radioenlace.",
    )
    oid_capacity_rx_kbps = forms.CharField(
        required=False, label="Capacidad RX (kbps)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.41112.1.4.7.1.18",
        }),
        help_text="Capacidad de recepción (Ubiquiti AirMax).",
    )
    oid_capacity_tx_kbps = forms.CharField(
        required=False, label="Capacidad TX (kbps)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.41112.1.4.7.1.19",
        }),
        help_text="Capacidad de transmisión (Ubiquiti AirMax).",
    )
    oid_noise_dbm = forms.CharField(
        required=False, label="Ruido (dBm)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.41112.1.4.5.1.8",
        }),
        help_text="Nivel de ruido del enlace (noise floor).",
    )
    oid_signal_dbm = forms.CharField(
        required=False, label="Señal (dBm)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.41112.1.4.5.1.5",
        }),
        help_text="Nivel de señal recibida (RSSI).",
    )
    oid_ccq_pct = forms.CharField(
        required=False, label="CCQ (%)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.41112.1.4.5.1.7",
        }),
        help_text="Calidad de la conexión (Client Connection Quality).",
    )
    oid_tx_rate_mbps = forms.CharField(
        required=False, label="Tasa TX (Mbps)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.41112.1.4.5.1.9",
        }),
        help_text="Tasa de transmisión actual.",
    )
    oid_rx_rate_mbps = forms.CharField(
        required=False, label="Tasa RX (Mbps)",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.41112.1.4.5.1.10",
        }),
        help_text="Tasa de recepción actual.",
    )
    oid_sta_count = forms.CharField(
        required=False, label="Clientes conectados",
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace form-control-sm",
            "placeholder": "1.3.6.1.4.1.41112.1.4.5.1.15",
        }),
        help_text="Número de estaciones asociadas al AP.",
    )

    # --- Editor JSON opcional ---
    oids_json = forms.CharField(
        required=False,
        label="Editar JSON de OIDs (avanzado)",
        widget=forms.Textarea(attrs={
            "class": "form-control font-monospace form-control-sm",
            "rows": 6,
            "placeholder": '{"cpu_pct": "1.3.6.1.4.1.41112.1.4.8.3.0", ...}',
        }),
        help_text=(
            "Editor directo del JSON. Si se rellena, **sobrescribe** "
            "los campos individuales de arriba. Útil para pegar "
            "configuraciones completas o para claves no listadas."
        ),
    )

    class Meta:
        model = DeviceModel
        fields = [
            "vendor", "name", "description", "is_wireless_link", "active",
        ]
        widgets = {
            "vendor": forms.Select(attrs={
                "class": "form-select",
                "autofocus": True,
            }),
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: LiteAP GPS, RB4011iGS+",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Notas opcionales sobre el modelo.",
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
        - Precarga el editor JSON con el contenido actual.
        - Bloquea el campo `vendor` si el modelo ya tiene equipos
          asociados.
        """
        super().__init__(*args, **kwargs)

        # Precargar OIDs existentes en los campos individuales
        if self.instance and self.instance.pk and self.instance.oids:
            for key in CHASSIS_OID_KEYS + RADIO_OID_KEYS:
                field_name = f"oid_{key}"
                if field_name in self.fields:
                    value = self.instance.oids.get(key, "")
                    if value:
                        self.fields[field_name].initial = value

            # Precargar el editor JSON
            self.fields["oids_json"].initial = json.dumps(
                self.instance.oids, indent=2, ensure_ascii=False
            )

        # Bloquear cambio de vendor si hay equipos asociados
        if self.instance and self.instance.pk and self.instance.devices.exists():
            self.fields["vendor"].disabled = True
            self.fields["vendor"].help_text = (
                "No puedes cambiar el fabricante: este modelo ya está "
                "siendo usado por uno o más equipos."
            )

    # ------------------------------------------------------------
    # VALIDACIÓN INDIVIDUAL DE CADA OID
    # ------------------------------------------------------------
    def clean_oid_cpu_pct(self):
        """Valida el OID de CPU."""
        return _validate_oid(self.cleaned_data.get("oid_cpu_pct"))

    def clean_oid_mem_pct(self):
        """Valida el OID de memoria (porcentaje)."""
        return _validate_oid(self.cleaned_data.get("oid_mem_pct"))

    def clean_oid_mem_used(self):
        """Valida el OID de memoria usada."""
        return _validate_oid(self.cleaned_data.get("oid_mem_used"))

    def clean_oid_mem_size(self):
        """Valida el OID de tamaño de memoria."""
        return _validate_oid(self.cleaned_data.get("oid_mem_size"))

    def clean_oid_mem_free(self):
        """Valida el OID de memoria libre."""
        return _validate_oid(self.cleaned_data.get("oid_mem_free"))

    def clean_oid_temp_c(self):
        """Valida el OID de temperatura."""
        return _validate_oid(self.cleaned_data.get("oid_temp_c"))

    def clean_oid_uptime(self):
        """Valida el OID de uptime."""
        return _validate_oid(self.cleaned_data.get("oid_uptime"))

    def clean_oid_freq_mhz(self):
        """Valida el OID de frecuencia."""
        return _validate_oid(self.cleaned_data.get("oid_freq_mhz"))

    def clean_oid_capacity_rx_kbps(self):
        """Valida el OID de capacidad de recepción."""
        return _validate_oid(self.cleaned_data.get("oid_capacity_rx_kbps"))

    def clean_oid_capacity_tx_kbps(self):
        """Valida el OID de capacidad de transmisión."""
        return _validate_oid(self.cleaned_data.get("oid_capacity_tx_kbps"))

    def clean_oid_noise_dbm(self):
        """Valida el OID de ruido."""
        return _validate_oid(self.cleaned_data.get("oid_noise_dbm"))

    def clean_oid_signal_dbm(self):
        """Valida el OID de señal."""
        return _validate_oid(self.cleaned_data.get("oid_signal_dbm"))

    def clean_oid_ccq_pct(self):
        """Valida el OID de CCQ."""
        return _validate_oid(self.cleaned_data.get("oid_ccq_pct"))

    def clean_oid_tx_rate_mbps(self):
        """Valida el OID de tasa de transmisión."""
        return _validate_oid(self.cleaned_data.get("oid_tx_rate_mbps"))

    def clean_oid_rx_rate_mbps(self):
        """Valida el OID de tasa de recepción."""
        return _validate_oid(self.cleaned_data.get("oid_rx_rate_mbps"))

    def clean_oid_sta_count(self):
        """Valida el OID de número de clientes."""
        return _validate_oid(self.cleaned_data.get("oid_sta_count"))

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

    def clean_oids_json(self):
        """
        Valida que el JSON sea un objeto válido y que cada valor sea
        un OID con formato correcto.

        Returns:
            str: el JSON en bruto (si es válido) o cadena vacía.

        Raises:
            forms.ValidationError: si el JSON no es un objeto o algún
                valor no es un OID válido.
        """
        raw = self.cleaned_data.get("oids_json")
        if not raw or not raw.strip():
            return ""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"JSON inválido: {e}")
        if not isinstance(data, dict):
            raise forms.ValidationError(
                "El JSON debe ser un objeto (clave-valor)."
            )
        # Validar que los valores sean strings de OIDs
        for key, val in data.items():
            if not isinstance(val, str) or not val.strip():
                raise forms.ValidationError(
                    f"El valor de '{key}' debe ser un OID no vacío."
                )
            _validate_oid(val)  # Lanza ValidationError si no es OID
        return raw

    # ------------------------------------------------------------
    # GUARDADO
    # ------------------------------------------------------------
    def save(self, commit=True):
        """
        Guarda el modelo reconstruyendo el dict `oids`.

        - Si `oids_json` tiene contenido, se usa ese JSON tal cual.
        - Si no, se construye a partir de los campos individuales.
        - Si todos los campos están vacíos, `oids` queda como `{}`,
          lo que activa el fallback a los OIDs por defecto del
          fabricante en el poller.

        Args:
            commit: si es True, guarda en la BD.

        Returns:
            DeviceModel: la instancia guardada (o no, si commit=False).
        """
        instance = super().save(commit=False)

        # Prioridad: JSON explícito > campos individuales
        raw_json = self.cleaned_data.get("oids_json", "").strip()
        if raw_json:
            instance.oids = json.loads(raw_json)
        else:
            oids = {}
            for key in CHASSIS_OID_KEYS + RADIO_OID_KEYS:
                value = self.cleaned_data.get(f"oid_{key}")
                if value:
                    oids[key] = value
            instance.oids = oids

        if commit:
            instance.save()
        return instance