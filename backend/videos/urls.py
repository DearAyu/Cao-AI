from rest_framework.routers import DefaultRouter

from .views import ImageJobViewSet, VideoJobViewSet

router = DefaultRouter()
router.register("video-jobs", VideoJobViewSet, basename="video-job")
router.register("image-jobs", ImageJobViewSet, basename="image-job")

urlpatterns = router.urls
