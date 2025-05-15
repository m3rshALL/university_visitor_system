
import random
from datetime import timedelta
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from faker import Faker

# Импортируйте ваши модели и статусы
from visitors.models import (
    Guest, Department, Visit, EmployeeProfile, StudentVisit,
    STATUS_AWAITING_ARRIVAL, STATUS_CHECKED_IN, STATUS_CHECKED_OUT, STATUS_CANCELLED
)

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populates the database with fake data for testing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--number',
            type=int,
            default=50,
            help='Number of fake visits (combined official and student) to create.'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing Visit, StudentVisit, Guest, and non-staff User/EmployeeProfile data before populating.'
        )

    def handle(self, *args, **options):
        fake = Faker('ru_RU') # Используем русскую локализацию для Faker
        number_of_visits_to_create = options['number']
        clear_data = options['clear']

        if clear_data:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Visit.objects.all().delete()
            StudentVisit.objects.all().delete()
            Guest.objects.all().delete()
            # Удаляем не-staff пользователей (их EmployeeProfile удалятся каскадно, если on_delete=CASCADE)
            User.objects.filter(is_staff=False).delete()
            # Department.objects.all().delete() # Раскомментируйте, если нужно очищать и департаменты
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        self.stdout.write(self.style.HTTP_INFO(f'Populating database with {number_of_visits_to_create} fake visits...'))

        # --- Создание Департаментов (если их нет или нужно больше) ---
        departments_to_create_names = ['Отдел кадров', 'Бухгалтерия', 'IT-отдел', 'Учебный отдел', 'Администрация', 'Деканат Школы Инженерии', 'Деканат Школы Цифровых Технологий']
        departments = []
        for dept_name in departments_to_create_names:
            department, created = Department.objects.get_or_create(name=dept_name)
            departments.append(department)
            if created:
                self.stdout.write(f'Created Department: {department.name}')

        if not departments:
            self.stdout.write(self.style.ERROR('No departments found or created. Please create departments first.'))
            return

        # --- Создание Сотрудников (Пользователей с EmployeeProfile) ---
        # Ensure we only get users who definitively have a department in their profile.
        host_employees = list(User.objects.filter(
            is_staff=False, employee_profile__isnull=False, employee_profile__department__isnull=False
        ).distinct())
        desired_employee_count = 20 # Желаемое количество сотрудников для тестирования

        if len(host_employees) < desired_employee_count:
            num_to_create = desired_employee_count - len(host_employees)
            self.stdout.write(f"Creating {num_to_create} new employees...")
            for _ in range(num_to_create):
                first_name = fake.first_name()
                last_name = fake.last_name()

                clean_first_name = "".join(filter(str.isalnum, first_name.lower()))
                clean_last_name = "".join(filter(str.isalnum, last_name.lower()))
                if not clean_first_name: clean_first_name = "user"
                if not clean_last_name: clean_last_name = str(random.randint(100,999))

                username_base = f"{clean_first_name}_{clean_last_name}"
                username = f"{username_base}{random.randint(1,99)}"
                while User.objects.filter(username=username).exists():
                    username = f"{username_base}{random.randint(100,9999)}"

                email = f"{clean_first_name}.{clean_last_name}@astanait.edu.kz"
                # Опциональная проверка уникальности email, если она строгая в модели User
                # email_base = f"{clean_first_name}.{clean_last_name}"
                # email_counter = 0
                # email = f"{email_base}@astanait.edu.kz"
                # while User.objects.filter(email=email).exists():
                #     email_counter += 1
                #     email = f"{email_base}{email_counter}@astanait.edu.kz"

                selected_department = random.choice(departments)

                try:
                    employee_user = User.objects.create_user(
                        username=username,
                        email=email,
                        password='password123', # Пароль для тестовых пользователей
                        first_name=first_name,
                        last_name=last_name,
                    )
                    # EmployeeProfile should be created by a signal.
                    # We fetch it and ensure it has a department.
                    profile, created_profile = EmployeeProfile.objects.get_or_create(user=employee_user)
                    if profile:
                        profile.department = selected_department
                        profile.phone_number = fake.phone_number()
                        profile.save()
                        # Add to host_employees only if profile is successfully updated with a department
                        if profile.department:
                            host_employees.append(employee_user)
                            self.stdout.write(f'Created/Updated Employee: {employee_user.get_full_name()} in {selected_department.name} (Email: {email})')
                        else:
                            self.stdout.write(self.style.WARNING(f'Employee {username} created but profile could not be assigned a department.'))
                    else: # Should not happen if get_or_create is used, but as a safeguard
                        self.stdout.write(self.style.WARNING(f'EmployeeProfile not found or created for {username}.'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Could not create employee {username} ({email}): {e}'))

        if not host_employees:
            self.stdout.write(self.style.WARNING('No host employees (User with EmployeeProfile and Department) found or created. Cannot create official visits, only student visits will be created if departments exist.'))
            # Не выходим, т.к. студенческие визиты могут быть созданы

        # --- Создание Гостей и Визитов ---
        visit_purposes_official = [
            'Деловая встреча', 'Собеседование', 'Подача документов',
            'Консультация', 'Личный вопрос', 'Получение справки', 'Мероприятие'
        ]
        visit_purposes_student = [
            'Поступление', 'Перевод', 'Консультация с эдвайзером',
            'Подача/Получение документов в деканат', 'Встреча с преподавателем', 'Библиотека'
        ]
        
        possible_visit_types = []
        if host_employees: # Можем создавать официальные визиты
            possible_visit_types.append('official')
        if departments: # Можем создавать студенческие визиты (нужен только департамент)
            possible_visit_types.append('student')

        if not possible_visit_types:
            self.stdout.write(self.style.ERROR('Cannot create any visits: no employees for official and no departments for student types.'))
            return

        staff_users = list(User.objects.filter(is_staff=True))
        if not staff_users: # Если нет staff, пусть регистрирует обычный сотрудник
            registered_by_candidates = host_employees
        else:
            registered_by_candidates = staff_users
        
        if not registered_by_candidates: # Крайний случай
            all_users = list(User.objects.all())
            if all_users:
                registered_by_candidates = all_users
            else:
                self.stdout.write(self.style.ERROR("CRITICAL: No users in DB to act as 'registered_by'. Cannot create visits."))
                return


        for i in range(number_of_visits_to_create):
            # Создание Гостя
            guest_full_name = fake.name()
            guest_iin = fake.numerify(text='############') # 12 цифр для ИИН
            guest_phone = fake.phone_number()
            guest_email = fake.email()

            guest, created = Guest.objects.get_or_create(
                iin=guest_iin,
                defaults={
                    'full_name': guest_full_name,
                    'phone_number': guest_phone,
                    'email': guest_email,
                }
            )
            if created:
                self.stdout.write(f'Created Guest: {guest.full_name} (IIN: {guest.iin})')
            else:
                # Обновляем данные существующего гостя, если они изменились
                guest.full_name = guest_full_name
                guest.phone_number = guest_phone
                guest.email = guest_email
                guest.save()
                self.stdout.write(f'Using existing Guest: {guest.full_name} (IIN: {guest.iin})')

            # Создание Визита
            chosen_visit_type = random.choice(possible_visit_types)
            registered_by_user = random.choice(registered_by_candidates)

            # Время визита
            days_offset = random.randint(-30, 5) # Визиты за последний месяц и на ближайшие 5 дней
            hour = random.randint(8, 17)
            minute = random.choice([0, 15, 30, 45])
            
            # Статусы и время
            status_choices = [STATUS_AWAITING_ARRIVAL, STATUS_CHECKED_IN, STATUS_CHECKED_OUT, STATUS_CANCELLED]
            status_probabilities = [0.3, 0.4, 0.25, 0.05]
            current_status = random.choices(status_choices, weights=status_probabilities, k=1)[0]
            
            entry_time = None
            exit_time = None
            # Для Visit (official) и StudentVisit с expected_entry_time
            expected_entry_time = timezone.now().replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_offset)

            if current_status == STATUS_CHECKED_IN:
                entry_time = expected_entry_time - timedelta(minutes=random.randint(0, 30))
                if entry_time > timezone.now(): # Если время входа в будущем
                    current_status = STATUS_AWAITING_ARRIVAL
                    entry_time = None
            elif current_status == STATUS_CHECKED_OUT:
                entry_time = expected_entry_time - timedelta(minutes=random.randint(0, 30))
                exit_time = entry_time + timedelta(hours=random.randint(0, 3), minutes=random.randint(15, 59))
                if entry_time > timezone.now(): # Если время входа в будущем
                    current_status = STATUS_AWAITING_ARRIVAL
                    entry_time = None
                    exit_time = None
                elif exit_time > timezone.now(): # Если время выхода в будущем, но вход уже был
                    current_status = STATUS_CHECKED_IN
                    exit_time = None
            
            # Для StudentVisit без expected_entry_time (если модель его не имеет или он не задан)
            # Модель StudentVisit не имеет expected_entry_time, поэтому эта логика для нее
            if chosen_visit_type == 'student':
                if current_status == STATUS_AWAITING_ARRIVAL: # Нелогично для студента без планирования, меняем
                    current_status = STATUS_CHECKED_IN if random.random() > 0.1 else STATUS_CHECKED_OUT # Большинство сразу входят
                
                if current_status == STATUS_CHECKED_IN:
                    entry_time = timezone.now() - timedelta(hours=random.randint(0,2), minutes=random.randint(0,59))
                    exit_time = None
                elif current_status == STATUS_CHECKED_OUT:
                    entry_time = timezone.now() - timedelta(days=random.randint(0,3), hours=random.randint(0,8), minutes=random.randint(0,59))
                    exit_time = entry_time + timedelta(hours=random.randint(0,3), minutes=random.randint(15,59))
                expected_entry_time = None # У StudentVisit нет этого поля

            if chosen_visit_type == 'official':
                if not host_employees: continue # Пропускаем, если нет сотрудников для официальных визитов

                employee_for_visit = random.choice(host_employees)
                # Defensive check for department in profile
                if not hasattr(employee_for_visit, 'employee_profile') or not employee_for_visit.employee_profile.department:
                    self.stdout.write(self.style.WARNING(
                        f"Skipping official visit for employee {employee_for_visit.username} due to missing department in profile."
                    ))
                    continue
                department_for_visit = employee_for_visit.employee_profile.department # Now this should be safe
                contact_phone = employee_for_visit.employee_profile.phone_number or fake.phone_number()
                visit_purpose = random.choice(visit_purposes_official)

                visit_data = {
                    'guest': guest,
                    'employee': employee_for_visit,
                    'department': department_for_visit,
                    'purpose': visit_purpose,
                    'expected_entry_time': expected_entry_time, # Для official visit
                    'status': current_status,
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'registered_by': registered_by_user,
                    'employee_contact_phone': contact_phone,
                    'consent_acknowledged': fake.boolean(chance_of_getting_true=80)
                }
                try:
                    visit = Visit.objects.create(**visit_data)
                    self.stdout.write(self.style.SUCCESS(f'Created Official Visit ID: {visit.id} for {guest.full_name} to {employee_for_visit.get_full_name()} ({current_status})'))
                except Exception as e:
                    logger.error(f'Error creating official visit for {guest.full_name}: {e}. Data: {visit_data}', exc_info=True)
                    self.stdout.write(self.style.ERROR(f'Error creating official visit for {guest.full_name}: {e}'))

            elif chosen_visit_type == 'student':
                if not departments: continue # Пропускаем, если нет департаментов

                department_for_visit = random.choice(departments)
                visit_purpose = random.choice(visit_purposes_student)
                
                student_visit_data = {
                    'guest': guest,
                    'department': department_for_visit,
                    'purpose': visit_purpose,
                    'status': current_status,
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'registered_by': registered_by_user,
                    'student_id_number': fake.numerify(text='STUD#####'),
                    'student_group': fake.bothify(text='??-##'),
                    'student_course': random.randint(1, 4),
                }
                try:
                    student_visit = StudentVisit.objects.create(**student_visit_data)
                    self.stdout.write(self.style.SUCCESS(f'Created Student Visit ID: {student_visit.id} for {guest.full_name} to {department_for_visit.name} ({current_status})'))
                except Exception as e:
                    logger.error(f'Error creating student visit for {guest.full_name}: {e}. Data: {student_visit_data}', exc_info=True)
                    self.stdout.write(self.style.ERROR(f'Error creating student visit for {guest.full_name}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully populated database with fake data.'))
