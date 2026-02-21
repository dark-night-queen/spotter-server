from rest_framework import routers

from django.urls import include, path

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
