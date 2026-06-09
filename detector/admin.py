from django.contrib import admin
from .models import VehicleLog

@admin.register(VehicleLog)
class VehicleLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle_type', 'direction', 'detected_time')
    list_filter = ('vehicle_type', 'direction')
    search_fields = ('vehicle_type',)
