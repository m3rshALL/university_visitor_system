# visitors/forms.py
from django import forms
from .models import Visit, Guest, StudentVisit, Department, EmployeeProfile, GuestInvitation
from departments.models import Department
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator
#Импортируем Django Select2 для виджета
from django_select2.forms import Select2Widget
from django_select2.forms import Select2MultipleWidget # Импорт для виджета множественного выбора
from django.urls import reverse_lazy
import logging
from django.utils import timezone
from notifications.tasks import send_visit_notification_task # Импортируем задачу Celery

from django.forms import formset_factory # Импортируем formset_factory для создания форм с несколькими экземплярами


logger = logging.getLogger(__name__)

# Определяем варианты выбора для цели визита
PURPOSE_CHOICES = [
    ('', '---------'), # Пустой выбор
    ('BUSINESS_MEETING', 'Деловая встреча'),
    ('PERSONAL_MEETING', 'Личный/Гостевой визит (к сотруднику)'),
    ('INTERVIEW', 'Собеседование'),
    ('NEGOTIATION', 'Переговоры / Подписание документов'), # Объединено
    ('SEMINAR_EVENT', 'Семинар / Мероприятие / Презентация'), # Объединено
    ('SERVICE_MAINTENANCE', 'Обслуживание / Ремонт / Доставка'), # Объединено
    ('COLLABORATION', 'Совместная работа / Исследование'),
    ('FILMING', 'Съемка'),
    ('AUDIT_INSPECTION', 'Проверка / Инспекция'),
    ('Other', 'Другое (укажите)'), # Ключ 'Other' будет использоваться в логике
]

# Определяем варианты выбора для цели визита студента
STUDENT_PURPOSE_CHOICES = [
    ('', '---------'),
    ('Admission', 'Поступление'),
    ('Transfer', 'Перевод'),
    ('Consultation', 'Консультация'),
    ('Documents', 'Подача/Получение документов'),
    ('Other', 'Другое'),
]

# --- Статусы визитов ---
STATUS_AWAITING_ARRIVAL = 'AWAITING'
STATUS_CHECKED_IN = 'CHECKED_IN'
STATUS_CHECKED_OUT = 'CHECKED_OUT'
STATUS_CANCELLED = 'CANCELLED'
VISIT_STATUS_CHOICES = [
    (STATUS_AWAITING_ARRIVAL, 'Ожидает прибытия'),
    (STATUS_CHECKED_IN, 'В здании'),
    (STATUS_CHECKED_OUT, 'Вышел'),
    (STATUS_CANCELLED, 'Отменен'),
]
# -----------------------



class GuestRegistrationForm(forms.Form):
    # --- Поля Гостя (остаются как были) ---
    guest_full_name = forms.CharField(label="ФИО гостя", max_length=255)
    guest_email = forms.EmailField(label="Email гостя (необязательно)", required=False)
    guest_phone = forms.CharField(label="Телефон гостя (обязательно)", max_length=20, required=True)
    guest_iin = forms.CharField(
        label="ИИН гостя (12 цифр, обязательно)", max_length=12, required=True,
        validators=[
            RegexValidator(regex=r'^\d{12}$', message='ИИН должен состоять ровно из 12 цифр.'),
            MinLengthValidator(12), MaxLengthValidator(12)
        ]
    )
    # --------------------------------------

    # --- Поля Визита ---
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        label="Департамент назначения",
        required=False, # Или True, в зависимости от логики clean() для типа 'OFFICIAL'
        widget=forms.Select(attrs={'id': 'id_visit_department'}) # <-- Добавим уникальный ID
    )
    employee = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).select_related('employee_profile'), # Можно добавить employee_profile
        label="Принимающий сотрудник",
        widget=Select2Widget(
            attrs={
                'data-placeholder': 'Сначала выберите департамент...', # Изменим placeholder
                # URL остается тот же, но JS будет добавлять параметр
                'data-ajax--url': reverse_lazy('employee_autocomplete'),
                # Зависимость будет управляться через JS
                'id': 'id_visit_employee' # <-- Добавим ID
                }
        ),
        required=False # Или True, проверяется в clean()
    )
    
    # Новое поле для планируемого времени
    expected_entry_time = forms.DateTimeField(
        label="Планируемая дата и время входа",
        required=False, # Обязательность будет управляться JS/View
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )

    # --- Измененное поле Цели визита ---
    purpose = forms.ChoiceField(
        choices=PURPOSE_CHOICES,
        label="Цель визита",
        required=True,
        widget=forms.Select(attrs={'id': 'id_purpose_choice'}) # Добавим ID для JS
    )
    # --- Новое текстовое поле для "Другое" ---
    purpose_other_text = forms.CharField(
        label="Укажите цель визита",
        required=False, # Будет обязательным через JS и валидацию формы
        widget=forms.TextInput(attrs={'id': 'id_purpose_other_text', 'placeholder': 'Введите цель визита'}) # Добавим ID
    )
    # ------------------------------------

    # --- Заменяем поле Email на поле выбора сотрудника ---
    # visiting_employee_email = forms.EmailField(label="Email принимающего сотрудника", required=True) # <-- Старое поле
    employee = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        label="Принимающий сотрудник",
        widget=Select2Widget(
            # Передаем attrs ОДИН раз со всеми нужными ключами
            attrs={
                'data-placeholder': 'Начните вводить ФИО или email...',
                'data-ajax--url': reverse_lazy('employee_autocomplete'),
                # Сюда же можно добавить другие data-атрибуты, если нужно
                # 'data-minimum-input-length': '2',
            }
        ),
        required=True
    )
    # ------------------------------------------------------
    employee_contact_phone_form = forms.CharField(
        label="Контактный тел. сотрудника", max_length=20, required=True
    )
    # -------------------
    
    # --- Новое поле Checkbox ---
    consent_acknowledged = forms.BooleanField(
        label="Я подтверждаю, что гость проинформирован об обработке его персональных данных согласно Закону РК и Политике конфиденциальности Университета.",
        required=True # Делаем поле обязательным
    )
    # --------------------------


    # --- Метод валидации для полей цели визита ---
    def clean(self):
        # Логика clean должна проверять employee/department/purpose
        # только если registration_mode (который придет из view) это предполагает.
        # Пока оставляем упрощенную валидацию "Другой цели".
        # Более сложная валидация будет зависеть от типа, выбранного на фронте.
        cleaned_data = super().clean()
        purpose_choice = cleaned_data.get('purpose')
        purpose_other = cleaned_data.get('purpose_other_text')
        if purpose_choice == 'Other' and not purpose_other:
            self.add_error('purpose_other_text', '...')
        # ...
        return cleaned_data
    # -----------------------------------------

    def save(self, registering_user, registration_type): # Принимает тип 'now' или 'later'
        # --- НАЧАЛО: Логика поиска/создания гостя ---
        guest_data = {
            'full_name': self.cleaned_data['guest_full_name'],
            'email': self.cleaned_data.get('guest_email'),
            'phone_number': self.cleaned_data.get('guest_phone'),
            'iin': self.cleaned_data.get('guest_iin'),
            # 'telegram_chat_id': self.cleaned_data.get('telegram_chat_id'), # Если добавили
        }
        guest = None # Инициализируем переменную
        created = False # Флаг, был ли гость создан

        guest_iin_value = guest_data.get('iin')
        # Ищем по ИИН, только если он не пустой
        if guest_iin_value:
            guest = Guest.objects.filter(iin=guest_iin_value).first()
            if guest:
                print(f"Найден существующий гость по ИИН: {guest.full_name}")
            else:
                print(f"Гость с ИИН {guest_iin_value} не найден, будет создан новый (или найден по ФИО).")


        if not guest:
             guest_full_name_value = guest_data.get('full_name')
             if not guest_full_name_value:
                 # Этого не должно быть при правильной настройке формы, но проверим
                 raise forms.ValidationError("Необходимо указать ФИО гостя.")

             # Ищем или создаем по ФИО (без учета регистра)
             guest, created = Guest.objects.get_or_create(
                 full_name__iexact=guest_full_name_value,
                 defaults=guest_data # Используем все данные при СОЗДАНИИ
             )
             if created:
                 print(f"Создан новый гость: {guest.full_name}")

        # Если гость был найден (по ИИН или ФИО), обновим его данные, если они изменились
        if not created:
            updated = False
            # Проходим по всем полям гостя из формы
            for field_name in ['full_name', 'email', 'phone_number', 'iin']: # Перечисляем поля модели Guest
                 form_value = guest_data.get(field_name)
                 # Обновляем, если в форме есть значение И оно отличается от значения в базе
                 if form_value and getattr(guest, field_name) != form_value:
                     setattr(guest, field_name, form_value)
                     updated = True
            if updated:
                 guest.save()
                 print(f"Обновлены данные для существующего гостя: {guest.full_name}")

        # Теперь переменная 'guest' гарантированно содержит ЭКЗЕМПЛЯР Guest
        logger.info(f"Using guest object: {guest} (ID: {guest.id}), Created: {created}")
        # --- КОНЕЦ: Логика поиска/создания гостя ---

        # --- Определяем цель визита ---
        purpose_to_save = self.cleaned_data.get('purpose')
        if purpose_to_save == 'Other':
            purpose_to_save = self.cleaned_data.get('purpose_other_text')
        # --------------------------

        # --- Создаем объект Visit, используя найденный/созданный guest ---
        visit = Visit(
            guest=guest, # <-- Теперь здесь правильный ОБЪЕКТ гостя
            employee=self.cleaned_data.get('employee'),
            department=self.cleaned_data.get('department'),
            purpose=purpose_to_save,
            registered_by=registering_user,
            employee_contact_phone=self.cleaned_data.get('employee_contact_phone_form'),
            expected_entry_time=self.cleaned_data.get('expected_entry_time'),
            consent_acknowledged=self.cleaned_data.get('consent_acknowledged', False) # <-- Сохраняем значение чекбокса
        )
        # -------------------------------------------------------------

        # --- Устанавливаем статус и время, отправляем уведомление ---
        if registration_type == 'now':
            visit.status = STATUS_CHECKED_IN
            visit.entry_time = timezone.now()
            logger.info(f"Visit {visit.id} created with status CHECKED_IN.")
        elif registration_type == 'later':
            visit.status = STATUS_AWAITING_ARRIVAL
            visit.entry_time = None
            logger.info(f"Visit {visit.id} created with status AWAITING_ARRIVAL.")
            # Отправляем уведомление только для запланированных
            if visit.expected_entry_time:
                 try:
                     visit.save() # Сохраняем ДО задачи
                     send_visit_notification_task.delay(visit.id, 'official')
                     logger.info(f"Celery task queued for Visit ID {visit.id}")
                 except Exception as e:
                     logger.error(f"Ошибка постановки задачи Celery для Visit {visit.id}: {e}", exc_info=True)
                     if not visit.pk: visit.save() # Пытаемся сохранить
            else:
                 logger.warning(f"Visit {visit.id} is 'later' but has no expected_entry_time.")
                 if not visit.pk: visit.save() # Сохраняем как ожидающий
        else:
             visit.status = STATUS_AWAITING_ARRIVAL # По умолчанию
             visit.entry_time = None
             logger.warning(f"Visit {visit.id} created with unknown registration_type '{registration_type}', setting status to AWAITING_ARRIVAL.")

        # Сохраняем объект в БД, если он не был сохранен ранее (в блоке try)
        if not visit.pk:
            visit.save()
        logger.info(f"Saved Visit ID {visit.id}, Status: {visit.status}, Consent Ack: {visit.consent_acknowledged}")
        # ---------------------------------------------------------

        return visit
    # -------------------------------------

# --- Новая форма для регистрации визитов студентов/абитуриентов ---
class StudentVisitRegistrationForm(forms.Form):
    # --- Поля Гостя (как в GuestRegistrationForm) ---
    guest_full_name = forms.CharField(label="ФИО посетителя", max_length=255)
    guest_email = forms.EmailField(label="Email (необязательно)", required=False)
    guest_phone = forms.CharField(label="Телефон (необязательно)", max_length=20, required=False)
    guest_iin = forms.CharField(
        label="ИИН (12 цифр, необязательно)", max_length=12, required=False,
        validators=[
            RegexValidator(regex=r'^\d{12}$', message='ИИН должен состоять ровно из 12 цифр.'),
            MinLengthValidator(12), MaxLengthValidator(12)
        ]
    )
    # -----------------------------------------------

    # --- Поля Студента/Абитуриента (необязательные) ---
    student_id_number = forms.CharField(label="ID Студента (если есть)", max_length=50, required=False)
    student_group = forms.CharField(label="Группа (если есть)", max_length=100, required=False)
    student_course = forms.IntegerField(label="Курс (если есть)", required=False, min_value=1, max_value=6)
    # -----------------------------------------------

    # --- Поля Визита Студента ---
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        label="Департамент назначения",
        required=True # Обязательно для этого типа визита
    )
    purpose = forms.ChoiceField(
        choices=STUDENT_PURPOSE_CHOICES,
        label="Цель визита",
        required=True,
        widget=forms.Select(attrs={'id': 'id_purpose_choice'}) # ID для JS
    )
    purpose_other_text = forms.CharField(
        label="Укажите цель визита",
        required=False, # Проверяется в clean()
        widget=forms.TextInput(attrs={'id': 'id_purpose_other_text', 'placeholder': 'Введите цель визита'}) # ID для JS
    )
    # --------------------------

    def clean(self):
        cleaned_data = super().clean()
        purpose_choice = cleaned_data.get('purpose')
        purpose_other = cleaned_data.get('purpose_other_text')

        if purpose_choice == 'Other' and not purpose_other:
            self.add_error('purpose_other_text', 'Пожалуйста, укажите цель визита, так как вы выбрали "Другое".')
        elif purpose_choice != 'Other' and purpose_other:
             cleaned_data['purpose_other_text'] = '' # Очищаем, если не "Другое"

        return cleaned_data

    def save(self, registering_user):
        # 1. Найти или создать Гостя
        guest_data = {
            'full_name': self.cleaned_data['guest_full_name'],
            'email': self.cleaned_data.get('guest_email'),
            'phone_number': self.cleaned_data.get('guest_phone'),
            'iin': self.cleaned_data.get('guest_iin'),
        }
        guest = None
        if guest_data['iin']:
            guest = Guest.objects.filter(iin=guest_data['iin']).first()
        if not guest:
             guest, created = Guest.objects.get_or_create(full_name=guest_data['full_name'], defaults=guest_data)
        else:
             created = False; updated = False # Обновляем существующего
             for field, value in guest_data.items():
                 if value and getattr(guest, field) != value: setattr(guest, field, value); updated = True
             if updated: guest.save()

        # 2. Определить цель визита
        purpose_to_save = self.cleaned_data.get('purpose')
        if purpose_to_save == 'Other':
            purpose_to_save = self.cleaned_data.get('purpose_other_text')

        # 3. Создать StudentVisit
        student_visit = StudentVisit.objects.create(
            guest=guest,
            student_id_number=self.cleaned_data.get('student_id_number'),
            student_group=self.cleaned_data.get('student_group'),
            student_course=self.cleaned_data.get('student_course'),
            department=self.cleaned_data.get('department'),
            purpose=purpose_to_save,
            registered_by=registering_user,
            # entry_time по умолчанию now()
        )
        return student_visit # Возвращаем созданный объект
# ----------------------------------------------------------------

# --- Новая форма для фильтрации общей истории ---
class HistoryFilterForm(forms.Form):
    # Общие поля для обоих типов визитов
    guest_name = forms.CharField(
        label='ФИО гостя содержит', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    guest_iin = forms.CharField(
        label='ИИН гостя содержит', required=False, max_length=12,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    entry_date_from = forms.DateField(
        label='Дата входа от', required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'})
    )
    entry_date_to = forms.DateField(
        label='Дата входа до', required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'})
    )
    purpose = forms.CharField(
        label='Цель визита содержит', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    # --- Обновленные Статусы для Фильтра ---
    HISTORY_STATUS_CHOICES = [
        ('', 'Любой статус'), # Пустой выбор - все статусы
        (STATUS_AWAITING_ARRIVAL, 'Ожидает прибытия'),
        (STATUS_CHECKED_IN, 'В здании'),
        (STATUS_CHECKED_OUT, 'Вышел'),
        (STATUS_CANCELLED, 'Отменен'),
    ]
    status = forms.ChoiceField(
        label='Статус',
        required=False,
        choices=HISTORY_STATUS_CHOICES, # Используем новый список
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    # ------------------------------------
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(), label='Департамент', required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    # Поле только для Visit (гости к сотрудникам)
    employee_info = forms.CharField(
        label='Сотрудник (ФИО/Email)', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )

    # Поля только для StudentVisit
    student_id_number = forms.CharField(
        label='ID Студента содержит', required=False, max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    student_group = forms.CharField(
        label='Группа содержит', required=False, max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    # Можно добавить и другие поля для StudentVisit, если нужно

# ----------------------------------------------

# --- Новая форма для настройки профиля ---
class ProfileSetupForm(forms.ModelForm):
    # Делаем поля обязательными на уровне формы
    phone_number = forms.CharField(
        label="Ваш рабочий телефон", required=True, max_length=50,
        widget=forms.TextInput(attrs={'placeholder': '+7 (XXX) XXX-XX-XX'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.order_by('name'), # Сортируем департаменты
        label="Ваш департамент", required=True,
        empty_label="Выберите департамент..." # Подсказка для пустого значения
    )    
    class Meta:
        model = EmployeeProfile
        fields = ['phone_number', 'department'] # Только эти поля
# -------------------------------------

class GuestInvitationFillForm(forms.ModelForm):
    guest_iin = forms.CharField(
        label="ИИН (12 цифр)",
        max_length=12,
        required=True,
        validators=[
            RegexValidator(regex=r'^\d{12}$', message='ИИН должен состоять ровно из 12 цифр.'),
            MinLengthValidator(12), 
            MaxLengthValidator(12)
        ],
        widget=forms.TextInput(attrs={
            'placeholder': '123456789012',
            'pattern': '[0-9]{12}',
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = GuestInvitation
        fields = ['guest_full_name', 'guest_email', 'guest_phone', 'guest_iin', 'guest_photo']
        widgets = {
            'guest_full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'}),
            'guest_iin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '123456789012',
                'pattern': '[0-9]{12}',
                'title': 'ИИН должен состоять ровно из 12 цифр.'
            }),            
            'guest_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ivan@example.com'}),
            'guest_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 700 123 45 67'}),
            'guest_photo': forms.ClearableFileInput(attrs={'accept': 'image/*', 'class': 'form-control'}),
        }

class GuestInvitationFinalizeForm(forms.ModelForm):
    visit_time = forms.DateTimeField(
        label="Время визита",
        required=True,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        }),
        help_text="Укажите планируемое время визита"
    )
    
    class Meta:
        model = GuestInvitation
        fields = ['visit_time']

