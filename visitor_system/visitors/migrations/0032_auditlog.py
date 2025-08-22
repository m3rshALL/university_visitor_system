from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('visitors', '0031_studentvisit_stud_visit_status_entry_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Время события')),
                ('action', models.CharField(choices=[('create', 'create'), ('update', 'update'), ('view', 'view')], max_length=16, verbose_name='Действие')),
                ('model', models.CharField(max_length=100, verbose_name='Модель')),
                ('object_id', models.CharField(max_length=64, verbose_name='ID объекта')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP')),
                ('user_agent', models.TextField(blank=True, null=True, verbose_name='User-Agent')),
                ('path', models.CharField(blank=True, max_length=512, null=True, verbose_name='Путь запроса')),
                ('method', models.CharField(blank=True, max_length=10, null=True, verbose_name='HTTP метод')),
                ('changes', models.JSONField(blank=True, null=True, verbose_name='Изменения')),
                ('extra', models.JSONField(blank=True, null=True, verbose_name='Доп. данные')),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_events', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Аудит событие',
                'verbose_name_plural': 'Аудит события',
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action'], name='audit_action_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['model', 'object_id'], name='audit_model_obj_idx'),
        ),
    ]


