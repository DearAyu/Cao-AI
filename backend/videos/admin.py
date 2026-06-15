from django.contrib import admin

from .models import ImageJob, VideoJob


@admin.register(VideoJob)
class VideoJobAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "status", "remote_task_id", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("prompt", "remote_task_id")


@admin.register(ImageJob)
class ImageJobAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "status", "remote_task_id", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("prompt", "remote_task_id")
