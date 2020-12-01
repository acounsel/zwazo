# Generated by Django 2.1.7 on 2019-02-15 19:58

from django.db import migrations, models
import zwazo.storage_backends


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0003_auto_20190214_1748'),
    ]

    operations = [
        migrations.AddField(
            model_name='prompt',
            name='sound_file',
            field=models.FileField(blank=True, null=True, storage=zwazo.storage_backends.PrivateMediaStorage(), upload_to='files/'),
        ),
    ]
