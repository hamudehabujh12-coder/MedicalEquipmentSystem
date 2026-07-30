from django.contrib import admin
from .models import (
    Device,
    PracticeSettings,
    DeviceDocument,
    GeneralDocument,
    UserProfile,
    HomeSlider,
)

from .models import TechnicianDocument

admin.site.register(TechnicianDocument)
from .models import Geraetart

@admin.register(Geraetart)
class GeraetartAdmin(admin.ModelAdmin):
    list_display = ("name", "aktiv")

    
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "inventory_number",
        "serial_number",
        "manufacturer",
        "practice",
        "area",
        "room",
        "next_stk",
    )

    search_fields = (
        "name",
        "inventory_number",
        "serial_number",
        "manufacturer",
    )

    list_filter = (
        "practice",
        "area",
        "manufacturer",
    )


admin.site.register(PracticeSettings)
admin.site.register(DeviceDocument)
admin.site.register(GeneralDocument)
admin.site.register(UserProfile)
admin.site.register(HomeSlider)


from .models import DashboardWidget

@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):

    list_display = (
        "widget_type",
        "standort",
        "geraetart",
        "visible",
        "order",
    )

    list_filter = (
        "widget_type",
        "visible",
        "standort",
        "geraetart",
    )

    list_editable = (
        "visible",
        "order",
    )

    ordering = (
        "order",
        "widget_type",
    )

from .models import SystemUpdate


@admin.register(SystemUpdate)
class SystemUpdateAdmin(admin.ModelAdmin):
    list_display = (
        "version",
        "release_date",
        "installed",
    )
