# Generated by Django 5.1.1 on 2024-11-09 22:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('UnWrapped', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customwrap',
            name='top_songs',
        ),
        migrations.AddField(
            model_name='customwrap',
            name='ad_time',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='llm_insights',
            field=models.JSONField(default={}),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='top_artist_month',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='top_artist_year',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='top_songs_6_month',
            field=models.JSONField(default={}),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='top_songs_month',
            field=models.JSONField(default={}),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='top_songs_year',
            field=models.JSONField(default={}),
        ),
    ]
