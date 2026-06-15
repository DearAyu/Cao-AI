from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("videos", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImageJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("aliyun", "阿里 wan2.7-image"), ("seedream", "字节 Seedream 4.5")], max_length=32)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("submitted", "Submitted"), ("processing", "Processing"), ("succeeded", "Succeeded"), ("failed", "Failed")], default="pending", max_length=24)),
                ("prompt", models.TextField(blank=True)),
                ("aspect_ratio", models.CharField(default="1:1", max_length=16)),
                ("size", models.CharField(default="2K", max_length=16)),
                ("count", models.PositiveSmallIntegerField(default=1)),
                ("source_image", models.FileField(upload_to="image_uploads/")),
                ("remote_task_id", models.CharField(blank=True, max_length=255)),
                ("result_images", models.JSONField(blank=True, default=list)),
                ("error_message", models.TextField(blank=True)),
                ("raw_request", models.JSONField(blank=True, default=dict)),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
