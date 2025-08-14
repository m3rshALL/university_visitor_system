from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
	help = "Send a test email to verify SMTP configuration"

	def add_arguments(self, parser):
		parser.add_argument('--to', required=True, help='Recipient email address')

	def handle(self, *args, **options):
		recipient = options['to']
		subject = 'Visitor System: Test Email'
		message = 'This is a test email from Visitor System.'
		sent = send_mail(
			subject,
			message,
			settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
			[recipient],
			fail_silently=False,
		)
		self.stdout.write(self.style.SUCCESS(f'Sent: {sent}'))


