from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("videos", "0003_videojob_model_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="videojob",
            name="resolution",
            field=models.CharField(default="720p", max_length=16),
        ),
    ]
