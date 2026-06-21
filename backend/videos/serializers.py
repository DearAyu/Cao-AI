from django.conf import settings
from rest_framework import serializers

from .models import ImageJob, VideoJob, VideoJobAsset


VIDEO_SOURCE_MAX_FILES = 3
VIDEO_SOURCE_MAX_BYTES = 50 * 1024 * 1024
VIDEO_SOURCE_ALLOWED_TYPES = {
    "image/png": VideoJobAsset.MediaType.IMAGE,
    "image/jpeg": VideoJobAsset.MediaType.IMAGE,
    "image/webp": VideoJobAsset.MediaType.IMAGE,
    "video/mp4": VideoJobAsset.MediaType.VIDEO,
    "video/quicktime": VideoJobAsset.MediaType.VIDEO,
    "video/webm": VideoJobAsset.MediaType.VIDEO,
}


class VideoJobSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)
    source_image_url = serializers.SerializerMethodField()
    source_asset_urls = serializers.SerializerMethodField()
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
            "resolution",
            "source_image",
            "source_image_url",
            "source_asset_urls",
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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        files = self.get_source_files(attrs)
        if not files:
            raise serializers.ValidationError({"source_image": "请至少上传 1 个素材。"})
        if len(files) > VIDEO_SOURCE_MAX_FILES:
            raise serializers.ValidationError({"source_files": f"最多只能上传 {VIDEO_SOURCE_MAX_FILES} 个素材。"})
        for file in files:
            content_type = getattr(file, "content_type", "") or ""
            if content_type not in VIDEO_SOURCE_ALLOWED_TYPES:
                raise serializers.ValidationError({"source_files": "仅支持 PNG/JPG/WEBP 图片和 MP4/MOV/WEBM 视频。"})
            if file.size > VIDEO_SOURCE_MAX_BYTES:
                raise serializers.ValidationError({"source_files": "单个素材不能超过 50MB。"})
        return attrs

    def create(self, validated_data):
        files = self.get_source_files(validated_data)
        if files and "source_image" not in validated_data:
            validated_data["source_image"] = files[0]
        job = super().create(validated_data)
        for index, file in enumerate(files):
            content_type = getattr(file, "content_type", "") or ""
            asset_file = job.source_image.name if index == 0 else file
            VideoJobAsset.objects.create(
                job=job,
                file=asset_file,
                media_type=VIDEO_SOURCE_ALLOWED_TYPES[content_type],
                original_name=getattr(file, "name", ""),
                size=getattr(file, "size", 0),
            )
        return job

    def get_source_files(self, attrs):
        request = self.context.get("request")
        if request:
            files = request.FILES.getlist("source_files")
            if files:
                return files
        source_image = attrs.get("source_image")
        return [source_image] if source_image else []

    def get_source_image_url(self, obj):
        return self.absolute_url(obj.source_image.url if obj.source_image else "")

    def get_source_asset_urls(self, obj):
        assets = obj.source_assets.all()
        if not assets and obj.source_image:
            return [
                {
                    "url": self.absolute_url(obj.source_image.url),
                    "media_type": "image",
                    "original_name": "",
                    "size": 0,
                }
            ]
        return [
            {
                "url": self.absolute_url(asset.file.url if asset.file else ""),
                "media_type": asset.media_type,
                "original_name": asset.original_name,
                "size": asset.size,
            }
            for asset in assets
        ]

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
