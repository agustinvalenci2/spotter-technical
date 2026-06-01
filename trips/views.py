from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from trips.models import TripPlan
from trips.serializers import (TripPlanRequestSerializer,
                               TripPlanResponseSerializer,
                               TripPlanSerializer)
from trips.services.eld_service import build_eld_logs
from trips.services.hos_service import build_schedule
from trips.services.route_service import build_route
from trips.services.summary_service import build_summary


class TripPlanView(APIView):
    def get(self, request: Request) -> Response:
        trip_plans = TripPlan.objects.order_by("-created_at")
        serializer = TripPlanSerializer(trip_plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        request_serializer = TripPlanRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        payload = request_serializer.validated_data

        route = build_route(
            current_location=payload["current_location"],
            pickup_location=payload["pickup_location"],
            dropoff_location=payload["dropoff_location"],
        )
        schedule = build_schedule(
            route=route,
            current_cycle_used=payload["current_cycle_used"],
        )
        eld_logs = build_eld_logs(schedule)
        summary = build_summary(
            schedule=schedule,
            eld_logs=eld_logs,
            current_cycle_used=payload["current_cycle_used"],
        )

        response_data = {
            "route": route,
            "schedule": schedule,
            "eld_logs": eld_logs,
            "summary": summary,
        }

        TripPlan.objects.create(
            current_location=payload["current_location"],
            pickup_location=payload["pickup_location"],
            dropoff_location=payload["dropoff_location"],
            current_cycle_used=payload["current_cycle_used"],
            route=route,
            schedule=schedule,
            eld_logs=eld_logs,
            summary=summary,
        )

        response_serializer = TripPlanResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
