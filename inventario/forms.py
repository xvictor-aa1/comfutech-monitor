# inventario/forms.py
from django import forms
from .models import Device, DeviceModel


class DeviceForm(forms.ModelForm):
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
        ip = self.cleaned_data.get("ip", "").strip()
        qs = Device.objects.filter(ip=ip)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un equipo con esta IP.")
        return ip

    def clean(self):
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
