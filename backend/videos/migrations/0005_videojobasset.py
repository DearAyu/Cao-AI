from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("videos", "0004_videojob_resolution"),
    ]

    operations = [
        migrations.CreateModel(
            name="VideoJobAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="video_assets/")),
                ("media_type", models.CharField(choices=[("image", "Image"), ("video", "Video")], max_length=16)),
                ("original_name", models.CharField(blank=True, max_length=255)),
                ("size", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="source_assets", to="videos.videojob"),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
    ]
