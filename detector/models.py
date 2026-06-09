from django.db import models


class VehicleLog(models.Model):
    object_id = models.IntegerField(db_index=True, default=0)
    vehicle_type = models.CharField(max_length=50, db_index=True)
    direction = models.CharField(max_length=10)
    confidence = models.FloatField(default=0.0)
    detected_time = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['detected_time', 'vehicle_type']),
            models.Index(fields=['vehicle_type', 'direction']),
        ]

    def __str__(self):
        return f"[{self.object_id}] {self.vehicle_type} ({self.direction}) @ {self.detected_time}"
