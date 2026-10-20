from django.contrib import admin
from .models import Device, Interface


class InterfaceInline(admin.TabularInline):
    model = Interface
    extra = 0
    fields = ("if_index", "if_name", "if_alias", "speed_display",
              "if_type", "oper_status", "monitored")
    readonly_fields = ("if_index", "if_name", "if_alias",
                       "speed_display", "if_type", "oper_status")
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def speed_display(self, obj):
        if not obj.if_speed_bps:
            return "N/A"
        return f"{obj.if_speed_bps / 1_000_000:.0f} Mbps"
    speed_display.short_description = "Velocidad"


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "ip", "device_type", "device_role",
        "vendor", "location", "interfaces_count", "active",
    )
    list_filter = ("device_role", "vendor", "device_type", "active")
    search_fields = ("name", "ip", "location")
    list_editable = ("active",)
    list_display_links = ("id", "name")
    inlines = [InterfaceInline]
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Identificación", {
            "fields": ("name", "ip", "device_type", "device_role",
                       "vendor", "location")
        }),
        ("Credenciales SNMP", {
            "fields": ("snmp_version", "snmp_community",
                       "snmp_user", "snmp_auth", "snmp_priv")
        }),
        ("Monitoreo", {
            "fields": ("tcp_ports", "active")
        }),
        ("Auditoría", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def interfaces_count(self, obj):
        total = obj.interfaces.count()
        monitored = obj.interfaces.filter(monitored=True).count()
        return f"{monitored} / {total}"
    interfaces_count.short_description = "Monitoreadas"


@admin.register(Interface)
class InterfaceAdmin(admin.ModelAdmin):
    list_display = (
        "id", "device", "if_index", "if_name", "if_alias",
        "speed_display", "oper_status", "monitored",
    )
    list_filter = ("monitored", "oper_status", "device__device_role")
    search_fields = ("device__name", "if_name", "if_alias")
    list_editable = ("monitored",)
    list_display_links = ("id", "if_name")
    raw_id_fields = ("device",)

    def speed_display(self, obj):
        if not obj.if_speed_bps:
            return "N/A"
        return f"{obj.if_speed_bps / 1_000_000:.0f} Mbps"
    speed_display.short_description = "Velocidad"
