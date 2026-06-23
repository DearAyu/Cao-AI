from django.db import models


class VideoJob(models.Model):
    class Provider(models.TextChoices):
        VOLCENGINE = "volcengine", "火山 Seedance"
        ALIYUN = "aliyun", "阿里万相"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"
        PROCESSING = "processing", "Processing"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    provider = models.CharField(max_length=32, choices=Provider.choices)
    model_name = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    prompt = models.TextField(blank=True)
    aspect_ratio = models.CharField(max_length=16, default="1:1")
    duration = models.PositiveSmallIntegerField(default=5)
    resolution = models.CharField(max_length=16, default="720p")
    source_image = models.FileField(upload_to="uploads/")
    remote_task_id = models.CharField(max_length=255, blank=True)
    result_video = models.FileField(upload_to="results/", blank=True)
    error_message = models.TextField(blank=True)
    raw_request = models.JSONField(default=dict, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_provider_display()} {self.status} #{self.pk}"


class VideoJobAsset(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    job = models.ForeignKey(VideoJob, related_name="source_assets", on_delete=models.CASCADE)
    file = models.FileField(upload_to="video_assets/")
    media_type = models.CharField(max_length=16, choices=MediaType.choices)
    original_name = models.CharField(max_length=255, blank=True)
    size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.media_type} asset for video job #{self.job_id}"


class ImageJob(models.Model):
    class Provider(models.TextChoices):
        ALIYUN = "aliyun", "阿里 wan2.7-image"
        SEEDREAM = "seedream", "字节 Seedream 4.5"

        OPENAI = "openai", "Image2模型"
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"
        PROCESSING = "processing", "Processing"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    provider = models.CharField(max_length=32, choices=Provider.choices)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    prompt = models.TextField(blank=True)
    aspect_ratio = models.CharField(max_length=16, default="1:1")
    size = models.CharField(max_length=16, default="2K")
    count = models.PositiveSmallIntegerField(default=1)
    source_image = models.FileField(upload_to="image_uploads/")
    remote_task_id = models.CharField(max_length=255, blank=True)
    result_images = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    raw_request = models.JSONField(default=dict, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_provider_display()} {self.status} #{self.pk}"
