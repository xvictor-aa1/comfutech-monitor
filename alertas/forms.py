# alertas/forms.py
"""
Formularios de la app `alertas`.

Incluye:
  - AlertRuleForm: crear/editar reglas con múltiples condicionales lógicos.
"""
import json
import logging

from django import forms
from django.core.exceptions import ValidationError

from inventario.models import Device
from .models import AlertRule

log = logging.getLogger(__name__)


class AlertRuleForm(forms.Form):
    """
    Formulario para crear o editar una regla de alerta.

    Los condicionales se envían como un JSON en el campo oculto
    `conditionals_json`, construido por JavaScript desde la UI.
    """

    name = forms.CharField(
        max_length=150, required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control", "autofocus": True,
            "placeholder": "Ej: Alerta de saturación core",
        }),
        label="Nombre de la regla",
    )

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control", "rows": 2,
            "placeholder": "Describe el propósito de esta regla (opcional)",
        }),
        label="Descripción",
    )

    conditionals_json = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
    )

    severity = forms.ChoiceField(
        choices=AlertRule.SEVERITY_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Prioridad",
        initial="warning",
    )

    custom_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control", "rows": 3,
            "id": "id_custom_message",
            "placeholder": "{device1} con {metric1} = {value1} (umbral {threshold1})",
        }),
        label="Mensaje personalizado",
    )

    telegram_enabled = forms.BooleanField(
        required=False, initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Notificar por Telegram",
    )

    telegram_cooldown_sec = forms.IntegerField(
        required=False, initial=600, min_value=60, max_value=86400,
        widget=forms.NumberInput(attrs={
            "class": "form-control", "min": 60, "step": 60,
        }),
        label="Cooldown Telegram (s)",
    )

    fire_once = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Disparar solo una vez",
    )

    skip_on_startup = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Omitir al iniciar el monitor",
    )

    enabled = forms.BooleanField(
        required=False, initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Regla activa",
    )

    # ============================================================
    # VALIDACIÓN DE CONDICIONALES
    # ============================================================
    def clean_conditionals_json(self):
        """
        Valida el JSON de condicionales:
          - Debe ser una lista de 1 a 5 elementos.
          - Cada condicional debe tener device, metric, operator,
            threshold y duration_sec válidos.
          - Devuelve la lista ya saneada.
        """
        raw = self.cleaned_data.get("conditionals_json") or ""

        # Parsear JSON
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            raise ValidationError(
                "Los condicionales no tienen un formato válido."
            )

        if not isinstance(data, list):
            raise ValidationError("Los condicionales deben ser una lista.")

        if len(data) == 0:
            raise ValidationError("Debe agregar al menos 1 condicional.")

        max_c = AlertRule.MAX_CONDITIONALS
        if len(data) > max_c:
            raise ValidationError(f"Máximo {max_c} condicionales permitidos.")

        # Validar cada condicional
        metric_labels = dict(AlertRule.METRIC_CHOICES)
        operator_labels = dict(AlertRule.OPERATOR_CHOICES)

        cleaned = []
        for i, cond in enumerate(data):
            prefix = f"Condicional {i+1}: "

            if not isinstance(cond, dict):
                raise ValidationError(f"{prefix}formato inválido.")

            # --- Device ---
            device_id = cond.get("device_id")
            if not device_id:
                raise ValidationError(f"{prefix}debe seleccionar un equipo.")
            try:
                device_id = int(device_id)
            except (ValueError, TypeError):
                raise ValidationError(f"{prefix}ID de equipo inválido.")
            if not Device.objects.filter(pk=device_id).exists():
                raise ValidationError(f"{prefix}el equipo no existe.")

            # --- Metric ---
            metric = cond.get("metric", "")
            if metric not in metric_labels:
                raise ValidationError(f"{prefix}métrica inválida.")

            # --- Operator ---
            operator = cond.get("operator", "")
            valid_ops = [op for op, _ in AlertRule.get_valid_operators(metric)]
            if operator not in valid_ops:
                operator = valid_ops[0] if valid_ops else "gte"

            # --- Threshold ---
            try:
                threshold = float(cond.get("threshold", 0))
            except (ValueError, TypeError):
                raise ValidationError(f"{prefix}umbral inválido.")

            # device_down: threshold 0 o 1
            if metric == "device_down":
                operator = "eq"
                threshold = 1 if int(threshold) == 1 else 0

            # --- Duration ---
            try:
                duration_sec = int(cond.get("duration_sec", 60))
            except (ValueError, TypeError):
                duration_sec = 60
            duration_sec = max(0, min(86400, duration_sec))

            # --- Logic ---
            logic = cond.get("logic")
            if i == 0:
                logic = None  # el primero no necesita lógica
            elif logic not in ("AND", "OR"):
                logic = "AND"

            cleaned.append({
                "device_id": device_id,
                "metric": metric,
                "operator": operator,
                "threshold": threshold,
                "duration_sec": duration_sec,
                "logic": logic,
            })

        return cleaned

    def clean_telegram_cooldown_sec(self):
        """Valida el cooldown mínimo."""
        cd = self.cleaned_data.get("telegram_cooldown_sec")
        if cd is None:
            return 600
        if cd < 60:
            raise ValidationError("El cooldown mínimo es de 60 segundos.")
        return cd

    # ============================================================
    # GUARDAR
    # ============================================================
    def save(self, rule: AlertRule = None, created_by=None) -> AlertRule:
        """
        Crea o actualiza una AlertRule.

        Args:
            rule: instancia existente para editar, o None para crear.
            created_by: usuario que crea la regla.

        Returns:
            AlertRule: la regla guardada.
        """
        data = self.cleaned_data

        if rule is None:
            rule = AlertRule()
            if created_by:
                rule.created_by = created_by

        rule.name = data["name"]
        rule.description = data.get("description", "")
        rule.conditionals = data["conditionals_json"]
        rule.severity = data["severity"]
        rule.custom_message = data.get("custom_message", "") or ""
        rule.telegram_enabled = bool(data.get("telegram_enabled"))
        rule.telegram_cooldown_sec = data.get("telegram_cooldown_sec") or 600
        rule.fire_once = bool(data.get("fire_once"))
        rule.skip_on_startup = bool(data.get("skip_on_startup"))
        rule.enabled = bool(data.get("enabled"))

        rule.save()
        return rule