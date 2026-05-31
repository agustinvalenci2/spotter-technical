from datetime import datetime
from typing import Any

from trips.schemas import TripSummary

JsonDict = dict[str, Any]

CYCLE_LIMIT_HOURS = 70
ON_DUTY_TYPES = {"driving", "pickup", "dropoff", "fuel"}


def build_summary(
    schedule: list[JsonDict],
    eld_logs: list[JsonDict],
    current_cycle_used: float,
) -> JsonDict:
    driving_hours = 0.0
    on_duty_hours = 0.0
    off_duty_hours = 0.0
    fuel_stops = 0
    breaks = 0

    for segment in schedule:
        duration = _duration_hours(segment["start"], segment["end"])
        segment_type = segment["type"]

        if segment_type == "driving":
            driving_hours += duration
        if segment_type in ON_DUTY_TYPES:
            on_duty_hours += duration
        if segment_type in {"off_duty", "break"}:
            off_duty_hours += duration
        if segment_type == "fuel":
            fuel_stops += 1
        if segment_type == "break":
            breaks += 1

    cycle_used_after_trip = current_cycle_used + on_duty_hours
    remaining_cycle_hours = max(CYCLE_LIMIT_HOURS - cycle_used_after_trip, 0)
    estimated_days = len(eld_logs)
    hos_compliant = (
        driving_hours <= 11 * estimated_days if estimated_days else True
    ) and cycle_used_after_trip <= CYCLE_LIMIT_HOURS

    summary = TripSummary(
        driving_hours=round(driving_hours, 2),
        on_duty_hours=round(on_duty_hours, 2),
        off_duty_hours=round(off_duty_hours, 2),
        remaining_cycle_hours=round(remaining_cycle_hours, 2),
        fuel_stops=fuel_stops,
        breaks=breaks,
        estimated_days=estimated_days,
        hos_compliant=hos_compliant,
    )
    return summary.model_dump(mode="json")


def _duration_hours(start_iso: str, end_iso: str) -> float:
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    return (end - start).total_seconds() / 3600
