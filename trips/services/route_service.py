import json
from datetime import datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework.exceptions import APIException

from trips.schemas import (Coordinate, LegDurations, Route, RouteCoordinates,
                           Stop)

DEFAULT_START = datetime(2026, 5, 26, 8, 0, 0)
METERS_PER_MILE = 1609.344
SECONDS_PER_HOUR = 3600
ORS_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
COORDINATE_MATCH_TOLERANCE = 0.00001

JsonDict = dict[str, Any]
Coordinates = dict[str, float]


class RouteProviderError(APIException):
    status_code = 502
    default_detail = "Could not build route with OpenRouteService."
    default_code = "route_provider_error"


def build_route(
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
) -> JsonDict:
    current_coordinates = geocode_location(current_location)
    pickup_coordinates = geocode_location(pickup_location)
    dropoff_coordinates = geocode_location(dropoff_location)
    route_points = build_route_points(
        current_coordinates,
        pickup_coordinates,
        dropoff_coordinates,
    )
    directions = get_directions(route_points)

    distance_miles = round(directions["distance"] / METERS_PER_MILE, 2)
    duration_hours = round(directions["duration"] / SECONDS_PER_HOUR, 2)
    current_to_pickup_hours, pickup_to_dropoff_hours = get_leg_durations(
        directions=directions,
        current_coordinates=current_coordinates,
        pickup_coordinates=pickup_coordinates,
        dropoff_coordinates=dropoff_coordinates,
    )

    route = Route(
        distance_miles=distance_miles,
        duration_hours=duration_hours,
        leg_durations_hours=LegDurations(
            current_to_pickup=round(current_to_pickup_hours, 2),
            pickup_to_dropoff=round(pickup_to_dropoff_hours, 2),
        ),
        coordinates=RouteCoordinates(
            current=format_coordinates(current_coordinates),
            pickup=format_coordinates(pickup_coordinates),
            dropoff=format_coordinates(dropoff_coordinates),
        ),
        polyline=directions["geometry"],
        stops=build_stops(
            current_location=current_location,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            current_to_pickup_hours=current_to_pickup_hours,
            total_drive_hours=duration_hours,
        ),
    )
    return route.model_dump(mode="json")


def build_route_points(
    current_coordinates: Coordinates,
    pickup_coordinates: Coordinates,
    dropoff_coordinates: Coordinates,
) -> list[Coordinates]:
    points = [current_coordinates, pickup_coordinates, dropoff_coordinates]
    route_points: list[Coordinates] = []

    for point in points:
        if route_points and same_coordinates(route_points[-1], point):
            continue
        route_points.append(point)

    return route_points


def get_leg_durations(
    directions: JsonDict,
    current_coordinates: Coordinates,
    pickup_coordinates: Coordinates,
    dropoff_coordinates: Coordinates,
) -> tuple[float, float]:
    leg_durations = [
        segment["duration"] / SECONDS_PER_HOUR for segment in directions["segments"]
    ]
    current_matches_pickup = same_coordinates(current_coordinates, pickup_coordinates)
    pickup_matches_dropoff = same_coordinates(pickup_coordinates, dropoff_coordinates)

    if current_matches_pickup and pickup_matches_dropoff:
        return 0, 0
    if current_matches_pickup:
        return 0, leg_durations[0] if leg_durations else 0
    if pickup_matches_dropoff:
        return leg_durations[0] if leg_durations else 0, 0

    current_to_pickup_hours = leg_durations[0] if leg_durations else 0
    pickup_to_dropoff_hours = (
        leg_durations[1]
        if len(leg_durations) > 1
        else directions["duration"] / SECONDS_PER_HOUR
    )
    return current_to_pickup_hours, pickup_to_dropoff_hours


def geocode_location(location: str) -> Coordinates:
    if not settings.OPENROUTESERVICE_API_KEY:
        raise RouteProviderError(
            "Set OPENROUTESERVICE_API_KEY to geocode and calculate routes."
        )

    query = urlencode(
        {
            "api_key": settings.OPENROUTESERVICE_API_KEY,
            "text": location,
            "size": 1,
        }
    )
    response = request_json(f"{ORS_GEOCODE_URL}?{query}")
    features = response.get("features", [])
    if not features:
        raise RouteProviderError(
            f"OpenRouteService could not geocode location: {location}"
        )

    longitude, latitude = features[0]["geometry"]["coordinates"]
    return {
        "lat": latitude,
        "lng": longitude,
    }


def get_directions(coordinates: list[Coordinates]) -> JsonDict:
    if len(coordinates) < 2:
        return {
            "distance": 0,
            "duration": 0,
            "geometry": "",
            "segments": [],
        }

    body = {
        "coordinates": [
            [coordinate["lng"], coordinate["lat"]] for coordinate in coordinates
        ],
        "radiuses": [-1] * len(coordinates),
    }
    response = request_json(
        ORS_DIRECTIONS_URL,
        method="POST",
        body=body,
        headers={"Authorization": settings.OPENROUTESERVICE_API_KEY},
    )
    routes = response.get("routes", [])
    if not routes:
        raise RouteProviderError("OpenRouteService did not return a route.")

    route = routes[0]
    summary = route["summary"]
    return {
        "distance": summary["distance"],
        "duration": summary["duration"],
        "geometry": route["geometry"],
        "segments": route.get("segments", []),
    }


def request_json(
    url: str,
    method: str = "GET",
    body: JsonDict | None = None,
    headers: dict[str, str] | None = None,
) -> JsonDict:
    request_headers = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8") or exc.reason
        raise RouteProviderError(f"OpenRouteService request failed: {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise RouteProviderError(f"OpenRouteService is unavailable: {exc}") from exc


def format_coordinates(coordinates: Coordinates) -> Coordinate:
    return Coordinate(
        lat=round(coordinates["lat"], 6),
        lng=round(coordinates["lng"], 6),
    )


def same_coordinates(first: Coordinates, second: Coordinates) -> bool:
    return (
        abs(first["lat"] - second["lat"]) <= COORDINATE_MATCH_TOLERANCE
        and abs(first["lng"] - second["lng"]) <= COORDINATE_MATCH_TOLERANCE
    )


def build_stops(
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
    current_to_pickup_hours: float,
    total_drive_hours: float,
) -> list[Stop]:
    pickup_start = DEFAULT_START
    pickup_eta = pickup_start + timedelta(hours=current_to_pickup_hours)
    dropoff_eta = pickup_start + timedelta(hours=total_drive_hours + 1)

    return [
        Stop(
            type="current",
            location=current_location,
            eta=pickup_start,
            duration_minutes=0,
        ),
        Stop(
            type="pickup",
            location=pickup_location,
            eta=pickup_eta,
            duration_minutes=60,
        ),
        Stop(
            type="dropoff",
            location=dropoff_location,
            eta=dropoff_eta,
            duration_minutes=60,
        ),
    ]
