from loguru import logger
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.trip.models import Trip
from apps.trip.serializers import TripDetailSerializer, TripListSerializer
from apps.trip.services.eld_service import EldService


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all().order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TripDetailSerializer
        return TripListSerializer

    def create(self, request, *args, **kwargs):
        logger.info(f"Received Trip creation request: {request.data}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        trip = serializer.save()
        logger.info(f"Trip created with ID: {trip.id}")

        try:
            logger.info(f"Starting ELD simulation for Trip ID: {trip.id}")
            service = EldService(trip.id)
            service.generate_full_trip()
        except Exception as e:
            logger.error(f"Error during ELD simulation for Trip ID {trip.id}: {str(e)}")
            trip.delete()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TripDetailSerializer(trip).data, status=status.HTTP_201_CREATED)
