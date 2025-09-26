from django.core.management.base import BaseCommand
import time
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Hikvision alert stream poller (stub)"

    def add_arguments(self, parser):
        parser.add_argument('--device-id', type=int, help='HikDevice id')

    def handle(self, *args, **options):
        device_id = options.get('device_id')
        logger.info('Starting alert stream poller device_id=%s', device_id)
        # Заглушка бесконечного цикла с backoff
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Hik alert stream stopped'))


