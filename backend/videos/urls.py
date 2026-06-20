from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ImageJobViewSet, PromptAnalysisView, PromptAssistantView, VideoJobViewSet

router = DefaultRouter()
router.register("video-jobs", VideoJobViewSet, basename="video-job")
router.register("image-jobs", ImageJobViewSet, basename="image-job")

urlpatterns = [
    path("prompt-analysis/", PromptAnalysisView.as_view(), name="prompt-analysis"),
    path("prompt-assistant/", PromptAssistantView.as_view(), name="prompt-assistant"),
] + router.urls
