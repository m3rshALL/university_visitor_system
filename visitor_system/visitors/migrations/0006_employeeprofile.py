# Generated by Django 5.2 on 2025-04-24 07:25

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('departments', '0001_initial'),
        ('visitors', '0005_studentvisit'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmployeeProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(blank=True, max_length=50, null=True, verbose_name='Рабочий телефон')),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employees', to='departments.department', verbose_name='Департамент сотрудника')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='employee_profile', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Профиль сотрудника',
                'verbose_name_plural': 'Профили сотрудников',
            },
        ),
    ]
