from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('realtime_dashboard', '0002_dashboardfilterpreset'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dashboardmetric',
            name='value',
            field=models.JSONField(default=dict, help_text='JSON данные с метрикой', verbose_name='Значение метрики'),
        ),
    ]


