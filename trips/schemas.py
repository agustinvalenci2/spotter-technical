from datetime import date, datetime

from pydantic import BaseModel


class Coordinate(BaseModel):
    lat: float
    lng: float


class RouteCoordinates(BaseModel):
    current: Coordinate
    pickup: Coordinate
    dropoff: Coordinate


class LegDurations(BaseModel):
    current_to_pickup: float
    pickup_to_dropoff: float


class Stop(BaseModel):
    type: str
    location: str
    eta: datetime
    duration_minutes: int


class Route(BaseModel):
    distance_miles: float
    duration_hours: float
    leg_durations_hours: LegDurations
    coordinates: RouteCoordinates
    polyline: str
    stops: list[Stop]


class ScheduleSegment(BaseModel):
    type: str
    start: datetime
    end: datetime
    location: str | None = None


class EldSegment(BaseModel):
    status: str
    type: str
    start: str
    end: str
    duration_hours: float
    location: str | None = None


class EldLog(BaseModel):
    date: date
    segments: list[EldSegment]


class TripSummary(BaseModel):
    driving_hours: float
    on_duty_hours: float
    off_duty_hours: float
    remaining_cycle_hours: float
    fuel_stops: int
    breaks: int
    estimated_days: int
    hos_compliant: bool
