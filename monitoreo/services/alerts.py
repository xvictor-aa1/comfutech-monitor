# monitoreo/services/alerts.py
"""
Motor de alertas basado en AlertRule.

Cada poller llama a `evaluate_metrics(device, {metric: value})` y el motor
evalúa las reglas que contienen ese device en alguno de sus condicionales.

Soporta reglas con 1-5 condicionales lógicos combinables con AND/OR.

Estado interno por condicional:
    _cond_states = {
        (rule_id, cond_index): {"first_seen": float, "last_value": float}
    }
"""
import logging
import math
import time
from threading import Lock
from typing import Optional

from django.utils import timezone

from alertas.models import Alert, AlertRule

log = logging.getLogger(__name__)

# Estado por condicional
_cond_states = {}
_rule_lock = Lock()

# Estado "regla disparada" para fire_once
_rule_fired = {}

# Marca de tiempo de arranque del monitor (warm-up)
_monitor_start_time = time.time()
WARMUP_SECONDS = 120


# ============================================================
# HELPERS
# ============================================================
def _safe_number(v):
    """Convierte a float seguro, descartando NaN/Inf/fuera de rango."""
    if v is None:
        return None
    try:
        f = float(v)
    except (ValueError, TypeError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    if abs(f) > 1e15:
        return None
    return f


def _is_monitor_warming_up() -> bool:
    """¿Estamos dentro de la ventana de warm-up?"""
    return (time.time() - _monitor_start_time) < WARMUP_SECONDS


def reset_startup_time():
    """Reinicia el warm-up (llamado al arrancar el scheduler)."""
    global _monitor_start_time
    _monitor_start_time = time.time()
    log.info("Warm-up del monitor reiniciado (%ds).", WARMUP_SECONDS)


def _check_operator(value: float, operator: str, threshold: float) -> bool:
    """Aplica un operador lógico entre value y threshold."""
    if operator == "gt":  return value > threshold
    if operator == "gte": return value >= threshold
    if operator == "lt":  return value < threshold
    if operator == "lte": return value <= threshold
    if operator == "eq":  return abs(value - threshold) < 0.001
    return False


# ============================================================
# CONSTRUCCIÓN DE MENSAJES
# ============================================================
def _build_placeholders(rule, conditionals_data, values):
    """
    Construye el diccionario de placeholders disponibles.

    Args:
        rule: instancia de AlertRule.
        conditionals_data: lista de dicts con device/metric/etc.
        values: lista de valores observados (uno por condicional).

    Returns:
        dict: {placeholder_name: value}
    """
    placeholders = {
        "rule_name": rule.name,
        "severity": rule.get_severity_display(),
        "conditionals_count": str(len(conditionals_data)),
        "timestamp": timezone.localtime().strftime("%d/%m/%Y %H:%M:%S"),
    }

    metric_labels = dict(AlertRule.METRIC_CHOICES)
    operator_labels = dict(AlertRule.OPERATOR_CHOICES)

    for i, cond in enumerate(conditionals_data):
        idx = i + 1
        device = cond.get("device")
        metric = cond.get("metric", "")
        operator = cond.get("operator", "")
        threshold = cond.get("threshold")
        value = values[i] if i < len(values) else None

        device_name = device.name if device else "—"
        device_ip = device.ip if device else "—"

        # Placeholders numerados (device1, device2, ...)
        placeholders[f"device{idx}"] = device_name
        placeholders[f"ip{idx}"] = device_ip
        placeholders[f"metric{idx}"] = metric_labels.get(metric, metric)
        placeholders[f"operator{idx}"] = operator_labels.get(operator, operator)
        placeholders[f"threshold{idx}"] = (
            f"{threshold:.2f}" if threshold is not None else "—"
        )
        placeholders[f"value{idx}"] = (
            f"{value:.2f}" if value is not None else "—"
        )

        # Placeholders sin número (del primer condicional)
        if i == 0:
            placeholders["device"] = device_name
            placeholders["ip"] = device_ip
            placeholders["metric"] = metric_labels.get(metric, metric)
            placeholders["operator"] = operator_labels.get(operator, operator)
            placeholders["threshold"] = (
                f"{threshold:.2f}" if threshold is not None else "—"
            )
            placeholders["value"] = (
                f"{value:.2f}" if value is not None else "—"
            )

    return placeholders


def _build_message(rule, conditionals_data, values) -> str:
    """
    Construye el mensaje de la alerta.
    Si hay custom_message, sustituye placeholders.
    Si no, genera un mensaje automático.
    """
    if rule.custom_message and rule.custom_message.strip():
        msg = rule.custom_message
        placeholders = _build_placeholders(rule, conditionals_data, values)

        # Sustituir placeholders (de más largo a más corto para evitar
        # que {device1} sea reemplazado por {device} parcialmente)
        import re
        def _replace(match):
            key = match.group(1)
            return placeholders.get(key, match.group(0))

        msg = re.sub(r"\{(\w+)\}", _replace, msg)
        return msg

    # Mensaje automático
    parts = []
    for i, cond in enumerate(conditionals_data):
        device = cond.get("device")
        metric = cond.get("metric", "")
        operator = cond.get("operator", "")
        threshold = cond.get("threshold")
        value = values[i] if i < len(values) else None

        metric_disp = dict(AlertRule.METRIC_CHOICES).get(metric, metric)
        op_disp = dict(AlertRule.OPERATOR_CHOICES).get(operator, operator)

        device_name = device.name if device else "—"
        val_str = f"{value:.2f}" if value is not None else "—"

        prefix = ""
        if i > 0 and cond.get("logic"):
            prefix = f" {cond['logic']} "

        parts.append(
            f"{prefix}[{device_name}] {metric_disp} {op_disp} "
            f"{threshold} (valor: {val_str})"
        )

    return " ".join(parts)


# ============================================================
# ALERTAS
# ============================================================
def has_active_alert_for_rule(device_id: int, rule_id: int) -> bool:
    """¿Existe una alerta activa de esta regla para este device?"""
    return Alert.objects.filter(
        device_id=device_id, rule_id=rule_id, status="activa",
    ).exists()


def _resolve_alert(rule, device):
    """Marca las alertas activas de esta regla/device como resueltas."""
    updated = Alert.objects.filter(
        device=device, rule=rule, status="activa",
    ).update(status="resuelta", resolved_at=timezone.now())
    if updated:
        log.info("Alerta auto-resuelta: %s / %s", device.name, rule.name)


def _create_alert(rule, conditionals_data, values):
    """
    Crea la alerta para la regla.
    El device asociado a la alerta es el del primer condicional.
    """
    # Determinar device principal para la alerta
    primary_device = conditionals_data[0].get("device") if conditionals_data else None
    if not primary_device:
        return None

    # Anti-duplicados
    if has_active_alert_for_rule(primary_device.id, rule.id):
        return None

    message = _build_message(rule, conditionals_data, values)

    # alert_type: primera métrica si hay 1 condicional, "multi_conditional" si hay varios
    if len(conditionals_data) == 1:
        alert_type = conditionals_data[0].get("metric", "unknown")
    else:
        alert_type = "multi_conditional"

    # Valor "representativo": el del primer condicional
    primary_value = values[0] if values else None

    alert = Alert.objects.create(
        device=primary_device,
        rule=rule,
        alert_type=alert_type,
        severity=rule.severity,
        message=message,
        value_observed=_safe_number(primary_value),
        threshold_value=_safe_number(conditionals_data[0].get("threshold")),
        status="activa",
    )
    log.warning("ALERTA %s: %s", rule.severity.upper(), message)

    # Notificar por Telegram
    if rule.telegram_enabled:
        try:
            from . import telegram
            has_custom = bool(rule.custom_message and rule.custom_message.strip())
            telegram.send_alert(
                severity=rule.severity,
                message=message,
                device=primary_device,
                rule=rule,
                append_context=not has_custom,
            )
        except Exception as e:
            log.error("Error enviando alerta a Telegram: %s", e)

    return alert


# ============================================================
# EVALUACIÓN DE UNA REGLA
# ============================================================
def _evaluate_rule(rule, device_values):
    """
    Evalúa una regla con múltiples condicionales.

    Args:
        rule: instancia de AlertRule.
        device_values: dict {device_id: {metric: value}}
    """
    # Skip warm-up
    if rule.skip_on_startup and _is_monitor_warming_up():
        return

    conditionals = rule.conditionals or []
    if not conditionals:
        return

    # Cargar instancias de Device una sola vez
    from inventario.models import Device
    device_ids = list({c.get("device_id") for c in conditionals if c.get("device_id")})
    devices_map = {d.id: d for d in Device.objects.filter(id__in=device_ids)}

    now = time.time()
    cond_results = []      # bool: si el condicional está actualmente "satisfecho"
    cond_ready = []        # bool: si ya cumplió su duración mínima
    cond_values = []       # valores observados por condicional
    conditionals_data = [] # datos del condicional enriquecidos con device

    for i, cond in enumerate(conditionals):
        did = cond.get("device_id")
        metric = cond.get("metric")
        operator = cond.get("operator")
        threshold = float(cond.get("threshold", 0))
        duration_sec = int(cond.get("duration_sec", 60))

        # Obtener valor actual
        values_for_device = device_values.get(did, {})
        value = values_for_device.get(metric)

        device = devices_map.get(did)

        conditionals_data.append({
            "device": device,
            "metric": metric,
            "operator": operator,
            "threshold": threshold,
            "duration_sec": duration_sec,
            "logic": cond.get("logic"),
        })
        cond_values.append(value)

        # Evaluar condición
        satisfied = False
        if value is not None:
            satisfied = _check_operator(value, operator, threshold)

        cond_results.append(satisfied)

        # Estado por condicional
        key = (rule.id, i)
        with _rule_lock:
            state = _cond_states.get(key)
            if satisfied:
                if state is None:
                    _cond_states[key] = {"first_seen": now, "last_value": value}
                    state = _cond_states[key]
                else:
                    state["last_value"] = value
            else:
                _cond_states.pop(key, None)
                state = None

        # ¿Listo por duración?
        if state and (now - state["first_seen"]) >= duration_sec:
            cond_ready.append(True)
        else:
            cond_ready.append(False)

    # ------------------------------------------------------------
    # Combinar según lógica AND/OR
    # ------------------------------------------------------------
    final_ready = cond_ready[0]
    for i in range(1, len(cond_ready)):
        logic = conditionals[i].get("logic") or "AND"
        if logic == "AND":
            final_ready = final_ready and cond_ready[i]
        else:  # OR
            final_ready = final_ready or cond_ready[i]

    # ------------------------------------------------------------
    # Disparar / auto-resolver
    # ------------------------------------------------------------
    primary_device = conditionals_data[0].get("device")

    if final_ready:
        # fire_once
        if rule.fire_once and _rule_fired.get(rule.id):
            return

        _create_alert(rule, conditionals_data, cond_values)

        with _rule_lock:
            _rule_fired[rule.id] = True
    else:
        # Resetear estado para permitir re-disparar en el futuro
        if any(cond_ready) or not any(cond_results):
            # Si la combinación ya no es "ready", pero antes lo fue
            with _rule_lock:
                was_fired = _rule_fired.pop(rule.id, None)

            if was_fired and primary_device:
                _resolve_alert(rule, primary_device)


# ============================================================
# EVALUACIÓN DE MÚLTIPLES MÉTRICAS
# ============================================================
def evaluate_metrics(device, metrics: dict):
    """
    Evalúa las reglas que contienen este device en algún condicional
    contra las métricas dadas.

    Args:
        device: instancia de Device.
        metrics: dict {metric: value} de este device.
    """
    if not metrics:
        return

    # Filtrar valores nulos
    metric_names = [k for k, v in metrics.items() if v is not None]
    if not metric_names:
        return

    # Buscar reglas que tengan este device Y alguna de estas métricas
    rules = AlertRule.objects.filter(enabled=True)

    matching_rules = []
    for rule in rules:
        for cond in rule.conditionals or []:
            if cond.get("device_id") == device.id and cond.get("metric") in metric_names:
                matching_rules.append(rule)
                break

    # Evaluar cada regla
    for rule in matching_rules:
        try:
            # Construir device_values desde los datos actuales
            # (el resto de devices se leerán desde el estado persistido o se
            # marcarán como None si no tenemos sus valores en este ciclo)
            device_values = {device.id: metrics}

            # Intentar leer valores cacheados de otros devices si están
            # disponibles en el estado (last_value)
            for i, cond in enumerate(rule.conditionals or []):
                did = cond.get("device_id")
                if did == device.id:
                    continue
                if did in device_values:
                    continue
                # Leer último valor del estado si existe
                key = (rule.id, i)
                with _rule_lock:
                    state = _cond_states.get(key)
                if state and state.get("last_value") is not None:
                    device_values.setdefault(did, {})
                    device_values[did][cond.get("metric")] = state["last_value"]

            _evaluate_rule(rule, device_values)
        except Exception as e:
            log.exception("Error evaluando regla '%s': %s", rule.name, e)


# ============================================================
# COMPATIBILIDAD CON API VIEJA
# ============================================================
def evaluate(device, metric: str, value: Optional[float], *args, **kwargs):
    """Compatibilidad: evalúa una sola métrica."""
    evaluate_metrics(device, {metric: value})


def has_active_alert(device_id: int, alert_type: str) -> bool:
    """Compatibilidad: existe alerta activa por tipo."""
    return Alert.objects.filter(
        device_id=device_id, alert_type=alert_type, status="activa",
    ).exists()


def load_thresholds_for(device):
    """Compatibilidad legacy."""
    return {}