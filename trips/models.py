from django.db import models


class TripPlan(models.Model):
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_used = models.DecimalField(max_digits=5, decimal_places=2)
    route = models.JSONField()
    schedule = models.JSONField()
    eld_logs = models.JSONField()
    summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.pickup_location} to {self.dropoff_location}"
