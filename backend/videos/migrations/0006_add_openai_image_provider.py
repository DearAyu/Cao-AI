from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("videos", "0005_videojobasset"),
    ]

    operations = [
        migrations.AlterField(
            model_name="imagejob",
            name="provider",
            field=models.CharField(
                choices=[
                    ("aliyun", "阿里 wan2.7-image"),
                    ("seedream", "字节 Seedream 4.5"),
                    ("openai", "Image2模型"),
                ],
                max_length=32,
            ),
        ),
    ]
