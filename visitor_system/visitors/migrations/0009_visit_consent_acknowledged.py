# Generated by Django 5.2 on 2025-04-29 05:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visitors', '0008_alter_studentvisit_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='visit',
            name='consent_acknowledged',
            field=models.BooleanField(default=False, verbose_name='Гость проинформирован об обработке ПДн'),
        ),
    ]
