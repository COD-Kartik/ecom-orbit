from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ChannelViewSet,
    ProductListingViewSet,
    channel_list,
    channel_delete,
    channel_toggle,
)

app_name = "channels"

router = DefaultRouter()
router.register(
    "channels",
    ChannelViewSet,
    basename="channel",
)

router.register(
    "listings",
    ProductListingViewSet,
    basename="listing",
)

urlpatterns = [

    # Dashboard UI
    path(
        "dashboard/channels/",
        channel_list,
        name="channel_list",
    ),

    path(
        "dashboard/channels/<int:pk>/delete/",
        channel_delete,
        name="channel_delete",
    ),

    path(
        "dashboard/channels/<int:pk>/toggle/",
        channel_toggle,
        name="channel_toggle",
    ),

    # REST APIs
    path(
        "api/",
        include(router.urls),
    ),
]