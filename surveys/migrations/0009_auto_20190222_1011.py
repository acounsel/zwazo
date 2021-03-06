# Generated by Django 2.1.7 on 2019-02-22 18:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0008_questionresponse_contact'),
    ]

    operations = [
        migrations.AddField(
            model_name='survey',
            name='goodbye_prompt',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='goodbye_surveys', to='surveys.Prompt'),
        ),
        migrations.AlterField(
            model_name='prompt',
            name='category',
            field=models.CharField(choices=[('numeric', 'Numeric'), ('text', 'Text'), ('yes_no', 'Yes/No'), ('welcome', 'Welcome'), ('goodbye', 'Goodbye')], max_length=50),
        ),
    ]
