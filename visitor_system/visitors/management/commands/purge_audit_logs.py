from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from visitors.models import AuditLog


class Command(BaseCommand):
    help = 'Удаляет старые записи аудита (по умолчанию старше 90 дней). Использование: purge_audit_logs --days 180'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=90, help='Сколько дней хранить логи (по умолчанию 90)')

    def handle(self, *args, **options):
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)
        qs = AuditLog.objects.filter(created_at__lt=cutoff)
        count = qs.count()
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f'Удалено {count} записей аудита старше {days} дней'))


