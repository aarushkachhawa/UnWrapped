# Generated by Django 5.1 on 2024-12-01 20:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('UnWrapped', '0005_customwrap_imagepath'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedback',
            name='email',
            field=models.EmailField(default='default@gmail.com', max_length=254),
            preserve_default=False,
        ),
    ]
