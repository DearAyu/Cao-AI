from django.contrib import admin

from .models import ImageJob, VideoJob, VideoJobAsset


class VideoJobAssetInline(admin.TabularInline):
    model = VideoJobAsset
    extra = 0
    readonly_fields = ("media_type", "original_name", "size", "created_at")


@admin.register(VideoJob)
class VideoJobAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "status", "remote_task_id", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("prompt", "remote_task_id")
    inlines = [VideoJobAssetInline]


@admin.register(ImageJob)
class ImageJobAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "status", "remote_task_id", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("prompt", "remote_task_id")
