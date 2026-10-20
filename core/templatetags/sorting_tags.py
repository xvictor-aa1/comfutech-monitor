# core/templatetags/sorting_tags.py
"""Template tag para generar encabezados de tabla ordenables."""
from django import template

register = template.Library()

@register.inclusion_tag("core/_sortable_th.html", takes_context=True)
def sortable_th(context, key, label, width=""):
    """
    Renderiza un <th> con enlace de ordenamiento.

    Uso en template:
        {% load sorting_tags %}
        {% sortable_th "fecha" "Fecha" "120px" %}
    """
    request = context["request"]
    current_sort = request.GET.get("sort", "")
    current_order = request.GET.get("order", "desc")

    # Construir URL preservando otros parámetros
    params = request.GET.copy()
    if current_sort == key and current_order == "desc":
        params["order"] = "asc"
    else:
        params["order"] = "desc"
    params["sort"] = key

    return {
        "key": key,
        "label": label,
        "width": width,
        "current_sort": current_sort,
        "current_order": current_order,
        "url": "?" + params.urlencode(),
    }
