from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("videos", "0002_imagejob"),
    ]

    operations = [
        migrations.AddField(
            model_name="videojob",
            name="model_name",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
