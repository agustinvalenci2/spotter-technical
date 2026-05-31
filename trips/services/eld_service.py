from collections import defaultdict
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any

from trips.schemas import EldLog, EldSegment

JsonDict = dict[str, Any]


class EldStatus(str, Enum):
    ON_DUTY = "on_duty"
    DRIVING = "driving"
    OFF_DUTY = "off_duty"


class SegmentType(str, Enum):
    PICKUP = "pickup"
    DROPOFF = "dropoff"
    DRIVING = "driving"
    OFF_DUTY = "off_duty"
    BREAK = "break"
    FUEL = "fuel"


ELD_STATUS_BY_SEGMENT_TYPE: dict[str, str] = {
    SegmentType.PICKUP.value: EldStatus.ON_DUTY.value,
    SegmentType.DROPOFF.value: EldStatus.ON_DUTY.value,
    SegmentType.DRIVING.value: EldStatus.DRIVING.value,
    SegmentType.OFF_DUTY.value: EldStatus.OFF_DUTY.value,
    SegmentType.BREAK.value: EldStatus.OFF_DUTY.value,
    SegmentType.FUEL.value: EldStatus.ON_DUTY.value,
}


def build_eld_logs(schedule: list[JsonDict]) -> list[JsonDict]:
    grouped_segments: defaultdict[str, list[EldSegment]] = defaultdict(list)

    for segment in schedule:
        start = datetime.fromisoformat(segment["start"])
        end = datetime.fromisoformat(segment["end"])

        for split_start, split_end in _split_segment_by_day(start, end):
            date_key = split_start.date().isoformat()
            eld_segment = EldSegment(
                status=ELD_STATUS_BY_SEGMENT_TYPE.get(
                    segment["type"], EldStatus.ON_DUTY.value
                ),
                type=segment["type"],
                start=split_start.time().isoformat(timespec="minutes"),
                end=split_end.time().isoformat(timespec="minutes"),
                duration_hours=round(
                    (split_end - split_start).total_seconds() / 3600, 2
                ),
                location=segment.get("location"),
            )
            grouped_segments[date_key].append(eld_segment)

    return [
        EldLog(date=date, segments=segments).model_dump(mode="json")
        for date, segments in sorted(grouped_segments.items())
    ]


def _split_segment_by_day(
    start: datetime,
    end: datetime,
) -> list[tuple[datetime, datetime]]:
    parts: list[tuple[datetime, datetime]] = []
    cursor = start

    while cursor < end:
        next_midnight = datetime.combine(cursor.date() + timedelta(days=1), time.min)
        split_end = min(end, next_midnight)
        parts.append((cursor, split_end))
        cursor = split_end

    return parts
