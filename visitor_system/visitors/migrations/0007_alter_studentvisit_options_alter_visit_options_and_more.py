# Generated by Django 5.2 on 2025-04-25 06:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visitors', '0006_employeeprofile'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='studentvisit',
            options={'ordering': ['-entry_time', '-expected_entry_time'], 'verbose_name': 'Визит студента/абитуриента', 'verbose_name_plural': 'Визиты студентов/абитуриентов'},
        ),
        migrations.AlterModelOptions(
            name='visit',
            options={'ordering': ['-entry_time', '-expected_entry_time'], 'permissions': [('can_view_visit_statistics', 'Может просматривать статистику визитов')], 'verbose_name': 'Визит (к сотруднику/другой)', 'verbose_name_plural': 'Визиты (к сотрудникам/другие)'},
        ),
        migrations.AddField(
            model_name='studentvisit',
            name='expected_entry_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Планируемое время входа'),
        ),
        migrations.AddField(
            model_name='studentvisit',
            name='status',
            field=models.CharField(choices=[('AWAITING', 'Ожидает прибытия'), ('CHECKED_IN', 'В здании'), ('CHECKED_OUT', 'Вышел'), ('CANCELLED', 'Отменен')], default='AWAITING', max_length=20, verbose_name='Статус'),
        ),
        migrations.AddField(
            model_name='visit',
            name='expected_entry_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Планируемое время входа'),
        ),
        migrations.AddField(
            model_name='visit',
            name='status',
            field=models.CharField(choices=[('AWAITING', 'Ожидает прибытия'), ('CHECKED_IN', 'В здании'), ('CHECKED_OUT', 'Вышел'), ('CANCELLED', 'Отменен')], default='AWAITING', max_length=20, verbose_name='Статус'),
        ),
        migrations.AlterField(
            model_name='studentvisit',
            name='entry_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Время фактического входа'),
        ),
        migrations.AlterField(
            model_name='visit',
            name='entry_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Время фактического входа'),
        ),
    ]
