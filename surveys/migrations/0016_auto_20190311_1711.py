# Generated by Django 2.1.7 on 2019-03-12 00:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0015_auto_20190311_1601'),
    ]

    operations = [
        migrations.AlterField(
            model_name='questionresponse',
            name='response',
            field=models.CharField(default='No Response', max_length=255),
        ),
    ]
