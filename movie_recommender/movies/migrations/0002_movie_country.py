# Generated by Django 5.1.5 on 2025-01-15 17:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='movie',
            name='country',
            field=models.CharField(default='Unknown', max_length=100),
        ),
    ]
