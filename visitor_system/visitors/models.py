# visitors/models.py
from django.db import models
from django.db.models import Index, Q
from django.contrib.auth.models import User # Стандартная модель пользователя Django
from departments.models import Department
from django.utils import timezone
from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator
from cryptography.fernet import Fernet, InvalidToken  # type: ignore
import base64
from django.conf import settings
import uuid
from django.contrib.auth import get_user_model

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

def get_fernet():
    key_str = getattr(settings, 'IIN_ENCRYPTION_KEY', '')
    if not key_str:
        # Генерируем временный ключ для дев-окружения, но не сохраняем
        # В проде ключ обязателен в окружении
        key = base64.urlsafe_b64encode(b'0'*32)
    else:
        # Ключ Fernet уже в base64 формате, просто кодируем в байты
        key = key_str.encode()
    return Fernet(key)


class Guest(models.Model):
    full_name = models.CharField(max_length=255, verbose_name="ФИО гостя")
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Email")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер телефона")
    # Можно добавить поле для документа, удостоверяющего личность
    # Храним шифрованный ИИН и дублируем цифровой хэш для поиска
    iin_encrypted = models.BinaryField(null=True, blank=True, editable=False, verbose_name="Зашифрованный ИИН")
    iin_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True, editable=False, verbose_name="Хэш ИИН (поиск)")

    def __str__(self):
        return self.full_name

    # Виртуальные аксессоры для удобства работы в коде и формах
    @property
    def iin(self):
        if not self.iin_encrypted:
            return None
        f = get_fernet()
        try:
            # Django BinaryField может возвращать memoryview, конвертируем в bytes
            encrypted_data = self.iin_encrypted
            if isinstance(encrypted_data, memoryview):
                encrypted_data = bytes(encrypted_data)
            decrypted = f.decrypt(encrypted_data)
            return decrypted.decode()
        except (InvalidToken, Exception):
            return None

    @iin.setter
    def iin(self, value: str | None):
        if value:
            # Валидация формальная на уровне модели (дополнительно есть на формах)
            if not value.isdigit() or len(value) != 12:
                raise ValueError("ИИН должен состоять ровно из 12 цифр.")
            f = get_fernet()
            self.iin_encrypted = f.encrypt(value.encode())
            # Хэш для поиска (безопаснее через односторонний SHA-256)
            import hashlib
            self.iin_hash = hashlib.sha256(value.encode()).hexdigest()
        else:
            self.iin_encrypted = None
            self.iin_hash = None

    class Meta:
        verbose_name = "Гость"
        verbose_name_plural = "Гости"

class VisitPurpose(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name='Название цели визита')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')

    class Meta:
        verbose_name = 'Цель визита'
        verbose_name_plural = 'Цели визитов'
        ordering = ['name']

    def __str__(self):
        return self.name

class VisitGroup(models.Model):
    group_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Например, 'Делегация из XYZ', 'Участники конференции ABC'",
        verbose_name='Название группы/мероприятия'
    )
    purpose = models.ForeignKey(
        VisitPurpose,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Основная цель визита группы'
    )
    purpose_other_text = models.TextField(
        blank=True,
        null=True,
        verbose_name="Уточнение цели (если 'Другое')"
    )
    expected_entry_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Планируемое время входа группы'
    )
    registration_time = models.DateTimeField(
        default=timezone.now,
        verbose_name='Время регистрации группы'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Примечания по группе'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Департамент назначения'
    )
    employee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        limit_choices_to={'is_staff': True},
        null=True,
        related_name='group_visits_responsible_for',
        verbose_name='Принимающий сотрудник (основной)'
    )
    registered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='registered_visit_groups',
        verbose_name='Зарегистрировал группу'
    )

    class Meta:
        verbose_name = 'Групповой визит'
        verbose_name_plural = 'Групповые визиты'
        ordering = ['-registration_time']

    def __str__(self):
        return f"{self.group_name} ({self.registration_time.strftime('%Y-%m-%d %H:%M')})"

class Visit(models.Model):
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, verbose_name="Гость")
    employee = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Принимающий сотрудник", related_name='visits_hosted') # Сотрудник из системы
    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name="Департамент назначения")
    purpose = models.TextField(verbose_name="Цель визита")
    visit_group = models.ForeignKey(
        VisitGroup,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='visits',
        verbose_name='Групповой визит'
    )
    entry_time = models.DateTimeField(
        blank=True, null=True, # Убрали default, ставится при check-in
        verbose_name="Время фактического входа"
    )
    exit_time = models.DateTimeField(blank=True, null=True, verbose_name="Время выхода")
    expected_entry_time = models.DateTimeField(
        blank=True, null=True, # Для предварительной регистрации
        verbose_name="Планируемое время входа"
    )
    status = models.CharField(
        max_length=20,
        choices=VISIT_STATUS_CHOICES,
        default=STATUS_AWAITING_ARRIVAL, # По умолчанию - ожидание
        verbose_name="Статус"
    )
    registered_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Кем зарегистрирован", related_name='visits_registered') # Сотрудник, который оформил пропуск
    employee_contact_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Контактный тел. сотрудника (для визита)"
    )
    # --- Новое поле для подтверждения информирования ---
    consent_acknowledged = models.BooleanField(
        default=False, # По умолчанию - не подтверждено
        verbose_name="Гость проинформирован об обработке ПДн"
    )
    # ------------------------------------------------

    def is_active(self):
        """Проверяет, находится ли гость еще в здании (статус CHECKED_IN)."""
        return self.status == STATUS_CHECKED_IN
    is_active.boolean = True
    is_active.short_description = 'В здании?'
    # -----------------------------------------------

    def __str__(self):
        status_display = dict(VISIT_STATUS_CHOICES).get(self.status, self.status)
        return f"Визит {self.guest} к {self.employee} ({status_display})"

    class Meta:
        verbose_name = "Визит (к сотруднику/другой)"
        verbose_name_plural = "Визиты (к сотрудникам/другие)"
        ordering = ['-entry_time', '-expected_entry_time'] # Сортировка
        permissions = [("can_view_visit_statistics", "Может просматривать статистику визитов")]
        indexes = [
            Index(fields=['status'], name='visit_status_idx'),
            Index(fields=['entry_time'], name='visit_entry_time_idx'),
            Index(fields=['exit_time'], name='visit_exit_time_idx'),
            Index(fields=['employee'], name='visit_employee_idx'),
            Index(fields=['department'], name='visit_department_idx'),
            Index(fields=['visit_group'], name='visit_group_idx'),
            Index(fields=['guest'], name='visit_guest_idx'),
            Index(name='visit_active_idx', fields=['status'], condition=Q(exit_time__isnull=True)),
            Index(name='visit_awaiting_idx', fields=['status'], condition=Q(status=STATUS_AWAITING_ARRIVAL)),
            # P1: составные индексы для частых фильтров/сортировок
            Index(fields=['status', 'entry_time'], name='visit_status_entry_idx'),
            Index(fields=['department', 'entry_time'], name='visit_dept_entry_idx'),
            Index(name='visit_active_dept_idx', fields=['department', 'status'], condition=Q(exit_time__isnull=True)),
        ]
        # -------------------------------------


# --- Новая модель для визитов Студентов/Абитуриентов ---
class StudentVisit(models.Model):
    # Связь с гостем (для ФИО, ИИН, контактов)
    guest = models.ForeignKey(
        Guest,
        on_delete=models.CASCADE, # Если удаляем гостя, удаляем и этот тип визита
        verbose_name="Посетитель (Гость)"
    )
    # Специфичные поля для студента/абитуриента (необязательные)
    student_id_number = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="ID Студента (если есть)"
    )
    student_group = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Группа (если есть)"
    )
    student_course = models.IntegerField(
        blank=True, null=True, verbose_name="Курс (если есть)"
    )
    # Департамент, куда идет студент (обязательно)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT, # Защищаем от удаления департамента, если есть визиты
        verbose_name="Департамент назначения"
        # null=False, blank=False по умолчанию - поле обязательное
    )
    # Цель визита (будем хранить текст)
    purpose = models.TextField(verbose_name="Цель визита")
    # Стандартные поля визита
    entry_time = models.DateTimeField(
        blank=True, null=True, verbose_name="Время фактического входа"
    )
    exit_time = models.DateTimeField(blank=True, null=True, verbose_name="Время выхода")
    status = models.CharField(
        max_length=20,
        choices=VISIT_STATUS_CHOICES, # Используем те же статусы
        default=STATUS_CHECKED_IN, # По умолчанию - CHECKED_IN (в здании)
        verbose_name="Статус"
    )
    registered_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name="Кем зарегистрирован",
        related_name='student_visits_registered' # Другое related_name
    )

    def is_active(self):
        return self.status == STATUS_CHECKED_IN
    is_active.boolean = True
    is_active.short_description = 'В здании?'

    def __str__(self):
        status_display = dict(VISIT_STATUS_CHOICES).get(self.status, self.status)
        return f"Визит студента {self.guest} в {self.department.name} ({status_display})"

    class Meta:
        verbose_name = "Визит студента/абитуриента"
        verbose_name_plural = "Визиты студентов/абитуриентов"
        ordering = ['-entry_time']
        permissions = [
            ("can_register_student_visit", "Может регистрировать визиты студентов/абитуриентов"),
        ]
        indexes = [
            Index(fields=['status'], name='student_visit_status_idx'),
            Index(fields=['entry_time'], name='student_visit_entry_time_idx'),
            Index(fields=['exit_time'], name='student_visit_exit_time_idx'),
            Index(fields=['department'], name='student_visit_department_idx'),
            Index(fields=['registered_by'], name='stud_visit_reg_by_idx'),
            Index(name='student_visit_active_idx', fields=['status'], condition=Q(exit_time__isnull=True)),
            # P1: составные индексы
            Index(fields=['status', 'entry_time'], name='stud_visit_status_entry_idx'),
            Index(fields=['department', 'entry_time'], name='stud_visit_dept_entry_idx'),
        ]
# ---------------------------------------------------

# --- Новая модель Профиля Сотрудника ---
class EmployeeProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, # Используем настройку, а не прямой импорт User
        on_delete=models.CASCADE, # При удалении User удаляем и профиль
        related_name='employee_profile', # Имя для обратной связи user.employee_profile
        verbose_name="Пользователь"
    )
    phone_number = models.CharField(
        max_length=50, # Можно увеличить длину
        blank=True,
        null=True,
        verbose_name="Рабочий телефон"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL, # При удалении департамента поле у юзера станет NULL
        null=True,
        blank=True, # Разрешаем сотрудника без департамента
        verbose_name="Департамент сотрудника",
        related_name='employees' # Имя для обратной связи department.employees.all()
    )

    def __str__(self):
        return f"Профиль для {self.user.get_full_name() or self.user.username}"

    class Meta:
        verbose_name = "Профиль сотрудника"
        verbose_name_plural = "Профили сотрудников"
# ------------------------------------

class GuestInvitation(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='guest_invitations', verbose_name="Пригласивший сотрудник")
    guest_full_name = models.CharField(max_length=255, verbose_name="ФИО гостя")
    guest_email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Email гостя")
    guest_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон гостя")
    guest_iin = models.CharField(
        max_length=12,
        validators=[
            RegexValidator(regex=r'^\d{12}$', message='ИИН должен состоять ровно из 12 цифр.'),
            MinLengthValidator(12), 
            MaxLengthValidator(12)
        ],
        blank=True,
        null=True,
        verbose_name="ИИН гостя"
    )
    # Для группп регистрации и отображения маски удобно хранить последние 4 цифры
    guest_iin_last4 = models.CharField(max_length=4, blank=True, null=True, editable=False)
    guest_photo = models.ImageField(upload_to='guest_photos/', blank=True, null=True, verbose_name="Фото гостя")
    created_at = models.DateTimeField(auto_now_add=True)
    is_filled = models.BooleanField(default=False, verbose_name="Гость заполнил данные")
    visit_time = models.DateTimeField(blank=True, null=True, verbose_name="Время визита")
    is_registered = models.BooleanField(default=False, verbose_name="Визит зарегистрирован")
    visit = models.OneToOneField('Visit', on_delete=models.SET_NULL, blank=True, null=True, related_name='invitation', verbose_name="Связанный визит")

    def __str__(self):
        return f"Приглашение для {self.guest_full_name} от {self.employee}"  

    class Meta:
        verbose_name = "Приглашение гостя"
        verbose_name_plural = "Приглашения гостей"

    def save(self, *args, **kwargs):
        # Обновляем guest_iin_last4
        if self.guest_iin and len(self.guest_iin) >= 4:
            self.guest_iin_last4 = self.guest_iin[-4:]
        else:
            self.guest_iin_last4 = None
        super().save(*args, **kwargs)

class GuestEntry(models.Model):
    invitation = models.ForeignKey(GuestInvitation, on_delete=models.CASCADE, related_name='entries')
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    iin = models.CharField(max_length=12, blank=True, null=True)
    photo = models.ImageField(upload_to='guest_photos/', blank=True, null=True)

class GroupInvitation(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_invitations', verbose_name="Пригласивший сотрудник")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name="Департамент назначения", blank=True, null=True)
    purpose = models.TextField(verbose_name="Цель визита", blank=True, null=True)
    visit_time = models.DateTimeField(verbose_name="Время визита", blank=True, null=True)
    exit_time = models.DateTimeField(blank=True, null=True, verbose_name="Время выхода")
    is_completed = models.BooleanField(default=False, verbose_name="Визит завершен")
    created_at = models.DateTimeField(auto_now_add=True)
    is_filled = models.BooleanField(default=False, verbose_name="Группа заполнена")
    is_registered = models.BooleanField(default=False, verbose_name="Визит зарегистрирован")
    group_name = models.CharField(max_length=255, verbose_name="Название группы", blank=True, null=True)

    def __str__(self):
        if self.visit_time:
            return f"Групповое приглашение от {self.employee} на {self.visit_time.strftime('%Y-%m-%d %H:%M')}"
        else:
            return f"Групповое приглашение от {self.employee} (время не указано)"

    class Meta:
        verbose_name = "Групповое приглашение"
        verbose_name_plural = "Групповые приглашения"

class GroupGuest(models.Model):
    group_invitation = models.ForeignKey(GroupInvitation, on_delete=models.CASCADE, related_name='guests', verbose_name="Групповое приглашение")
    full_name = models.CharField(max_length=255, verbose_name="ФИО гостя")
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Email гостя")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон гостя")
    iin = models.CharField(
        max_length=12,
        validators=[
            RegexValidator(regex=r'^\d{12}$', message='ИИН должен состоять ровно из 12 цифр.'),
            MinLengthValidator(12),
            MaxLengthValidator(12)
        ],
        blank=True,
        null=True,
        verbose_name="ИИН гостя"
    )
    iin_last4 = models.CharField(max_length=4, blank=True, null=True, editable=False)
    photo = models.ImageField(upload_to='group_guests/', blank=True, null=True, verbose_name="Фото гостя")
    is_filled = models.BooleanField(default=False, verbose_name="Гость заполнил данные")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} (групповой гость)"

    class Meta:
        verbose_name = "Гость группы"
        verbose_name_plural = "Гости группы"

    def save(self, *args, **kwargs):
        # Обновляем iin_last4
        if self.iin and len(self.iin) >= 4:
            self.iin_last4 = self.iin[-4:]
        else:
            self.iin_last4 = None
        super().save(*args, **kwargs)


# --- Журнал аудита действий над визитами и просмотров ---
class AuditLog(models.Model):
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_VIEW = 'view'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'create'),
        (ACTION_UPDATE, 'update'),
        (ACTION_VIEW, 'view'),
    ]

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Время события')
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, verbose_name='Действие')
    model = models.CharField(max_length=100, verbose_name='Модель')
    object_id = models.CharField(max_length=64, verbose_name='ID объекта')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_events', verbose_name='Пользователь')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')
    user_agent = models.TextField(null=True, blank=True, verbose_name='User-Agent')
    path = models.CharField(max_length=512, null=True, blank=True, verbose_name='Путь запроса')
    method = models.CharField(max_length=10, null=True, blank=True, verbose_name='HTTP метод')
    changes = models.JSONField(null=True, blank=True, verbose_name='Изменения')
    extra = models.JSONField(null=True, blank=True, verbose_name='Доп. данные')

    class Meta:
        verbose_name = 'Аудит событие'
        verbose_name_plural = 'Аудит события'
        indexes = [
            Index(fields=['action'], name='audit_action_idx'),
            Index(fields=['model', 'object_id'], name='audit_model_obj_idx'),
        ]

    def __str__(self) -> str:  # type: ignore[override]
        return f"{self.created_at.isoformat()} {self.action} {self.model}:{self.object_id} by {getattr(self.actor, 'username', '-') }"
