# Generated by Django 5.1.1 on 2024-12-01 09:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("UnWrapped", "0003_customwrap_top_songs_artists"),
    ]

    operations = [
        migrations.AddField(
            model_name="customwrap",
            name="top_songs_urls",
            field=models.JSONField(default=list),
        ),
    ]
