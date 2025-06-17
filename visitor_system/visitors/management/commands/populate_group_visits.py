# Management command to populate test data for group invitations and guests

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from visitors.models import GroupInvitation, GroupGuest
from departments.models import Department
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Populate test data: group invitations and associated guests.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--num',
            type=int,
            default=5,
            help='Number of group invitations to create'
        )
        parser.add_argument(
            '--guests-per-group',
            dest='guests_per_group',
            type=int,
            default=10,
            help='Number of guests per invitation'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username of employee to assign invitations to'
        )

    def handle(self, *args, **options):
        num = options['num']
        guests_per_group = options['guests_per_group']
        specified_username = options.get('user')
        
        User = get_user_model()
        
        # Если указан конкретный пользователь, используем его
        if specified_username:
            staff_users = list(User.objects.filter(username=specified_username))
            if not staff_users:
                self.stderr.write(f'User {specified_username} not found.')
                return
        else:
            staff_users = list(User.objects.filter(is_staff=True))
            
        departments = list(Department.objects.all())
        if not staff_users or not departments:
            self.stderr.write('No staff users or departments found.')
            return

        for i in range(num):
            creator = random.choice(staff_users)
            dept = random.choice(departments)
            purpose = f"Test group visit {i+1}"
            # Устанавливаем время визита на будущее (от 1 до 14 дней)
            visit_time = datetime.now() + timedelta(days=random.randint(1, 14))

            # Создаем групповое приглашение
            invitation = GroupInvitation.objects.create(
                employee=creator,
                department=dept,
                purpose=purpose,
                visit_time=visit_time,
                is_filled=True,  # Устанавливаем сразу при создании!
                is_registered=False,  # Явно устанавливаем False
            )
            
            # Создаем гостей для приглашения
            for j in range(guests_per_group):
                full_name = f"Guest_{i+1}_{j+1}"
                email = f"guest_{i+1}_{j+1}@example.com"
                phone_number = f"+7{random.randint(7000000000, 7999999999)}"  # Исправил длину номера
                iin = str(random.randint(100000000000, 999999999999))
                
                GroupGuest.objects.create(
                    group_invitation=invitation,
                    full_name=full_name,
                    email=email,
                    phone_number=phone_number,
                    iin=iin,
                    is_filled=True,
                )
            
            # ВАЖНОЕ ИЗМЕНЕНИЕ: не используем update_fields при сохранении
            # Это может блокировать обновление, если есть другая логика в save()
            # invitation.is_filled = True
            # invitation.save(update_fields=['is_filled'])
            
            # Вместо этого мы установили is_filled=True при создании приглашения
            
            self.stdout.write(self.style.SUCCESS(
                f"Created invitation ID {invitation.pk} with {guests_per_group} guests for {creator.username}."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Successfully created {num} invitations, each with {guests_per_group} guests."
        ))