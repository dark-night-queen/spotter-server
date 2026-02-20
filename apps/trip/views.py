from rest_framework import viewsets, status
from rest_framework.response import Response
from apps.trip.models import Trip
from apps.trip.serializers import TripListSerializer, TripDetailSerializer
from apps.trip.services.eld_service import EldService


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all().order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TripDetailSerializer
        return TripListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_is_valid(raise_exception=True)

        # 1. Save the Trip
        trip = serializer.save()

        # 2. Run the Simulation
        try:
            service = EldService(trip.id)
            service.generate_full_trip()
        except Exception as e:
            # If geo-service fails or logic breaks, cleanup and return error
            trip.delete()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Return the detailed view of the generated trip
        return Response(TripDetailSerializer(trip).data, status=status.HTTP_201_CREATED)
