from rest_framework import serializers


class TripPlanRequestSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=255)
    pickup_location = serializers.CharField(max_length=255)
    dropoff_location = serializers.CharField(max_length=255)
    current_cycle_used = serializers.FloatField(min_value=0, max_value=70)


class StopSerializer(serializers.Serializer):
    type = serializers.CharField()
    location = serializers.CharField()
    eta = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField()


class CoordinateSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class RouteCoordinatesSerializer(serializers.Serializer):
    current = CoordinateSerializer()
    pickup = CoordinateSerializer()
    dropoff = CoordinateSerializer()


class LegDurationsSerializer(serializers.Serializer):
    current_to_pickup = serializers.FloatField()
    pickup_to_dropoff = serializers.FloatField()


class RouteSerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    duration_hours = serializers.FloatField()
    leg_durations_hours = LegDurationsSerializer()
    coordinates = RouteCoordinatesSerializer()
    polyline = serializers.CharField()
    stops = StopSerializer(many=True)


class ScheduleSegmentSerializer(serializers.Serializer):
    type = serializers.CharField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    location = serializers.CharField(required=False)


class EldLogSerializer(serializers.Serializer):
    date = serializers.DateField()
    segments = serializers.ListField()


class TripSummarySerializer(serializers.Serializer):
    driving_hours = serializers.FloatField()
    on_duty_hours = serializers.FloatField()
    off_duty_hours = serializers.FloatField()
    remaining_cycle_hours = serializers.FloatField()
    fuel_stops = serializers.IntegerField()
    breaks = serializers.IntegerField()
    estimated_days = serializers.IntegerField()
    hos_compliant = serializers.BooleanField()


class TripPlanResponseSerializer(serializers.Serializer):
    route = RouteSerializer()
    schedule = ScheduleSegmentSerializer(many=True)
    eld_logs = EldLogSerializer(many=True)
    summary = TripSummarySerializer()
