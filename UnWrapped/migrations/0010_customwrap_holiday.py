# Generated by Django 5.1.1 on 2024-11-28 17:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("UnWrapped", "0009_alter_feedback_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="customwrap",
            name="holiday",
            field=models.CharField(default="none", max_length=20),
        ),
    ]