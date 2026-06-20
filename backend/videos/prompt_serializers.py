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


class PromptAssistantRequestSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["generate", "revise"], default="generate")
    product_title = serializers.CharField(max_length=300, allow_blank=True)
    product_detail = serializers.CharField(max_length=3000, allow_blank=True)
    selling_points = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        default=list,
    )
    current_prompt = serializers.CharField(max_length=2500, allow_blank=True, required=False, default="")
    revision_instruction = serializers.CharField(max_length=1000, allow_blank=True, required=False, default="")

    def validate(self, attrs):
        action = attrs.get("action", "generate")
        if action == "generate":
            if not attrs.get("product_title", "").strip():
                raise serializers.ValidationError({"product_title": "请填写商品标题"})
            if not attrs.get("product_detail", "").strip():
                raise serializers.ValidationError({"product_detail": "请填写商品详情"})
        if action == "revise":
            if not attrs.get("current_prompt", "").strip():
                raise serializers.ValidationError({"current_prompt": "缺少当前提示词"})
            if not attrs.get("revision_instruction", "").strip():
                raise serializers.ValidationError({"revision_instruction": "请填写修改要求"})
        return attrs
