# Generated by Django 5.1 on 2024-12-01 08:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('UnWrapped', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customwrap',
            name='hindi_mood1',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='hindi_mood2',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='hindi_mood3',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='hindi_mood4',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='hindi_mood5',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='hindi_mood6',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='mandarin_mood1',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='mandarin_mood2',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='mandarin_mood3',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='mandarin_mood4',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='mandarin_mood5',
            field=models.CharField(default='Unknown', max_length=500),
        ),
        migrations.AddField(
            model_name='customwrap',
            name='mandarin_mood6',
            field=models.CharField(default='Unknown', max_length=500),
        ),
    ]
