from django.conf import settings
from rest_framework import serializers

from .models import ImageJob, VideoJob


class VideoJobSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)
    source_image_url = serializers.SerializerMethodField()
    result_video_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoJob
        fields = [
            "id",
            "provider",
            "provider_label",
            "model_name",
            "status",
            "prompt",
            "aspect_ratio",
            "duration",
            "source_image",
            "source_image_url",
            "remote_task_id",
            "result_video",
            "result_video_url",
            "error_message",
            "raw_request",
            "raw_response",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "remote_task_id",
            "result_video",
            "error_message",
            "raw_request",
            "raw_response",
            "created_at",
            "updated_at",
        ]

    def get_source_image_url(self, obj):
        return self.absolute_url(obj.source_image.url if obj.source_image else "")

    def get_result_video_url(self, obj):
        return self.absolute_url(obj.result_video.url if obj.result_video else "")

    def absolute_url(self, url):
        if not url:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class ImageJobSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)
    source_image_url = serializers.SerializerMethodField()
    result_image_urls = serializers.SerializerMethodField()

    class Meta:
        model = ImageJob
        fields = [
            "id",
            "provider",
            "provider_label",
            "status",
            "prompt",
            "aspect_ratio",
            "size",
            "count",
            "source_image",
            "source_image_url",
            "remote_task_id",
            "result_images",
            "result_image_urls",
            "error_message",
            "raw_request",
            "raw_response",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "remote_task_id",
            "result_images",
            "error_message",
            "raw_request",
            "raw_response",
            "created_at",
            "updated_at",
        ]

    def validate_count(self, value):
        if value < 1 or value > 4:
            raise serializers.ValidationError("图片张数需在 1 到 4 之间。")
        return value

    def get_source_image_url(self, obj):
        return self.absolute_url(obj.source_image.url if obj.source_image else "")

    def get_result_image_urls(self, obj):
        return [self.absolute_url(f"{settings.MEDIA_URL}{path}") for path in obj.result_images]

    def absolute_url(self, url):
        if not url:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url
