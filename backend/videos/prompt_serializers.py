from django.conf import settings
from rest_framework import serializers


class PromptAnalysisRequestSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def validate_image(self, value):
        if value.size > settings.PROVIDER_IMAGE_MAX_BYTES:
            raise serializers.ValidationError(
                f"图片大小不能超过 {settings.PROVIDER_IMAGE_MAX_BYTES} 字节。"
            )
        return value
