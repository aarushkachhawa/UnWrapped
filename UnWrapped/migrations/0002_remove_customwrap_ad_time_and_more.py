# Generated by Django 5.1.1 on 2024-11-22 20:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("UnWrapped", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="customwrap",
            name="ad_time",
        ),
        migrations.RemoveField(
            model_name="customwrap",
            name="llm_insights",
        ),
        migrations.RemoveField(
            model_name="customwrap",
            name="top_artist_month",
        ),
        migrations.RemoveField(
            model_name="customwrap",
            name="top_artist_year",
        ),
        migrations.RemoveField(
            model_name="customwrap",
            name="top_songs_year",
        ),
        migrations.AddField(
            model_name="customwrap",
            name="ads_minutes",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="artist1",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="artist2",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="artist3",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="content",
            field=models.TextField(default=None),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="hour_hand_rotation",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="image",
            field=models.TextField(default=None),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="image_url",
            field=models.TextField(default=None),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="latest_time",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="minute_hand_rotation",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="mood",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="mood1",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="mood2",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="mood3",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="mood4",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="mood5",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="mood6",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="premium",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="season",
            field=models.CharField(default="Seasonal", max_length=20),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="songPath",
            field=models.TextField(default=None),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="song_artist1",
            field=models.TextField(default="Unknown"),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="song_artist2",
            field=models.TextField(default="Unknown"),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="song_artist3",
            field=models.TextField(default="Unknown"),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="song_artist4",
            field=models.TextField(default="Unknown"),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="song_artist5",
            field=models.TextField(default="Unknown"),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="song_artist6",
            field=models.TextField(default="Unknown"),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="time_ranges",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="top_3_artists",
            field=models.TextField(default=list),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="top_artist",
            field=models.CharField(default="Unknown", max_length=500),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="top_songs",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="customwrap",
            name="total_minutes",
            field=models.FloatField(default=0),
        ),
    ]