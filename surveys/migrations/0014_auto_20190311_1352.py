# Generated by Django 2.1.7 on 2019-03-11 20:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0013_auto_20190225_1501'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='repeater',
            field=models.CharField(blank=True, max_length=2),
        ),
        migrations.AddField(
            model_name='question',
            name='terminator',
            field=models.CharField(blank=True, max_length=2),
        ),
        migrations.AlterField(
            model_name='project',
            name='email',
            field=models.CharField(choices=[('off', 'None'), ('oneway', 'One-Way'), ('twoway', 'Two-Way')], default='off', max_length=20),
        ),
        migrations.AlterField(
            model_name='project',
            name='sms',
            field=models.CharField(choices=[('off', 'None'), ('oneway', 'One-Way'), ('twoway', 'Two-Way')], default='off', max_length=20),
        ),
        migrations.AlterField(
            model_name='project',
            name='voice',
            field=models.CharField(choices=[('off', 'None'), ('oneway', 'One-Way'), ('twoway', 'Two-Way')], default='off', max_length=20),
        ),
        migrations.AlterField(
            model_name='project',
            name='whatsapp',
            field=models.CharField(choices=[('off', 'None'), ('oneway', 'One-Way'), ('twoway', 'Two-Way')], default='off', max_length=20),
        ),
    ]
