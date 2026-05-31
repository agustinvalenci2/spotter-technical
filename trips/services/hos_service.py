from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from trips.schemas import ScheduleSegment

JsonDict = dict[str, Any]

DRIVING_LIMIT_HOURS = 11
ON_DUTY_LIMIT_HOURS = 14
DRIVE_BEFORE_BREAK_HOURS = 8
BREAK_DURATION_HOURS = 0.5
FUEL_STOP_DURATION_HOURS = 0.5
FUEL_INTERVAL_MILES = 1000
DAILY_RESET_HOURS = 10
PICKUP_DURATION_HOURS = 1
DROPOFF_DURATION_HOURS = 1
CYCLE_LIMIT_HOURS = 70
DEFAULT_START = datetime(2026, 5, 26, 8, 0, 0)


@dataclass
class DrivingState:
    cursor: datetime
    miles_per_hour: float
    on_duty_used: float = 0
    drive_today: float = 0
    drive_since_break: float = 0
    miles_since_fuel: float = 0
    schedule: list[JsonDict] = field(default_factory=list)


def build_schedule(route: JsonDict, current_cycle_used: float) -> list[JsonDict]:
    distance_miles = route["distance_miles"]
    duration_hours = route["duration_hours"]
    miles_per_hour = (distance_miles / duration_hours) if duration_hours > 0 else 0

    leg_durations = route.get("leg_durations_hours", {})
    current_to_pickup_hours = leg_durations.get("current_to_pickup", 0)
    pickup_to_dropoff_hours = leg_durations.get(
        "pickup_to_dropoff", duration_hours
    )

    state = DrivingState(cursor=DEFAULT_START, miles_per_hour=miles_per_hour)

    _drive_leg(state, current_to_pickup_hours)
    _append_on_duty(
        state,
        segment_type="pickup",
        duration_hours=PICKUP_DURATION_HOURS,
        location=_stop_location(route, "pickup"),
    )
    _drive_leg(state, pickup_to_dropoff_hours)
    _append_on_duty(
        state,
        segment_type="dropoff",
        duration_hours=DROPOFF_DURATION_HOURS,
        location=_stop_location(route, "dropoff"),
    )

    return state.schedule


def _drive_leg(state: DrivingState, leg_hours: float) -> None:
    remaining = round(leg_hours, 4)
    while remaining > 0:
        if (
            state.drive_today >= DRIVING_LIMIT_HOURS
            or state.on_duty_used >= ON_DUTY_LIMIT_HOURS
        ):
            _append_off_duty_reset(state)
            continue

        if state.drive_since_break >= DRIVE_BEFORE_BREAK_HOURS:
            _append_break(state)
            continue

        if state.miles_since_fuel >= FUEL_INTERVAL_MILES:
            _append_fuel_stop(state)
            continue

        max_chunks = [
            remaining,
            DRIVING_LIMIT_HOURS - state.drive_today,
            ON_DUTY_LIMIT_HOURS - state.on_duty_used,
            DRIVE_BEFORE_BREAK_HOURS - state.drive_since_break,
        ]
        if state.miles_per_hour > 0:
            miles_until_fuel = FUEL_INTERVAL_MILES - state.miles_since_fuel
            max_chunks.append(miles_until_fuel / state.miles_per_hour)

        chunk = min(max_chunks)
        if chunk <= 0:
            _append_off_duty_reset(state)
            continue

        _append_segment(state, "driving", chunk)
        state.drive_today += chunk
        state.on_duty_used += chunk
        state.drive_since_break += chunk
        state.miles_since_fuel += chunk * state.miles_per_hour
        remaining = round(remaining - chunk, 4)


def _append_on_duty(
    state: DrivingState,
    segment_type: str,
    duration_hours: float,
    location: str | None = None,
) -> None:
    if (
        state.on_duty_used + duration_hours > ON_DUTY_LIMIT_HOURS
        and state.on_duty_used > 0
    ):
        _append_off_duty_reset(state)

    _append_segment(state, segment_type, duration_hours, location=location)
    state.on_duty_used += duration_hours


def _append_break(state: DrivingState) -> None:
    _append_segment(state, "break", BREAK_DURATION_HOURS)
    state.on_duty_used += BREAK_DURATION_HOURS
    state.drive_since_break = 0


def _append_fuel_stop(state: DrivingState) -> None:
    _append_segment(state, "fuel", FUEL_STOP_DURATION_HOURS)
    state.on_duty_used += FUEL_STOP_DURATION_HOURS
    state.miles_since_fuel = 0


def _append_off_duty_reset(state: DrivingState) -> None:
    _append_segment(state, "off_duty", DAILY_RESET_HOURS)
    state.on_duty_used = 0
    state.drive_today = 0
    state.drive_since_break = 0


def _append_segment(
    state: DrivingState,
    segment_type: str,
    duration_hours: float,
    location: str | None = None,
) -> None:
    end = state.cursor + timedelta(hours=duration_hours)
    segment = ScheduleSegment(
        type=segment_type,
        start=state.cursor,
        end=end,
        location=location,
    )
    state.schedule.append(segment.model_dump(mode="json", exclude_none=True))
    state.cursor = end


def _stop_location(route: JsonDict, stop_type: str) -> str | None:
    for stop in route.get("stops", []):
        if stop["type"] == stop_type:
            return stop["location"]
    return None
