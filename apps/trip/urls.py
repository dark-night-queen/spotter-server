from django.urls import path, include
from rest_framework import routers
from apps.trip import views

# versioning
API_VERSION = "v1"

# Initialize Router
trip = routers.DefaultRouter()
trip.register(r"trips", viewset=views.TripViewSet, basename="trip")

# urlpatterns
urlpatterns = [
    path(f"{API_VERSION}/", include((trip.urls, "trip"), namespace=API_VERSION)),
]
