# visitors/models.py
from django.db import models
from django.contrib.auth.models import User # Стандартная модель пользователя Django
from departments.models import Department
from django.utils import timezone
from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator
from django.conf import settings
from django.utils.translation import gettext_lazy as _

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

class Guest(models.Model):
    full_name = models.CharField(max_length=255, verbose_name="ФИО гостя")
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Email")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер телефона")
    # Можно добавить поле для документа, удостоверяющего личность
    iin = models.CharField(
        max_length=12,
        validators=[
            RegexValidator(regex=r'^\d{12}$', message='ИИН должен состоять ровно из 12 цифр.'),
            MinLengthValidator(12), # Дополнительная проверка длины
            MaxLengthValidator(12)
        ],
        null=True,
        unique=True, # Установить True, если ИИН должен быть уникальным для каждого гостя
        verbose_name="ИИН гостя"
    )

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Гость"
        verbose_name_plural = "Гости"

class Visit(models.Model):
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, verbose_name="Гость")
    visit_group = models.ForeignKey(
        'VisitGroup',
        verbose_name="Групповой визит",
        on_delete=models.CASCADE,
        null=True, blank=True, # Поле не обязательно
        related_name='visits' # Связь с группой визитов
    )
    employee = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Принимающий сотрудник", related_name='visits_hosted') # Сотрудник из системы
    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name="Департамент назначения")
    purpose = models.TextField(verbose_name="Цель визита")
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

# Define VisitPurpose before models that reference it directly
class VisitPurpose(models.Model):
    name = models.CharField(
        _("Название цели визита"),
        max_length=200,
        unique=True
    )
    description = models.TextField(_("Описание"), blank=True, null=True)

    class Meta:
        verbose_name = _("Цель визита")
        verbose_name_plural = _("Цели визитов")
        ordering = ['name']

    def __str__(self):
        return self.name

class VisitGroup(models.Model):
    """Модель для группового визита."""
    group_name = models.CharField(
        _("Название группы/мероприятия"),
        max_length=255,
        blank=True,
        help_text=_("Например, 'Делегация из XYZ', 'Участники конференции ABC'")
    )
    department = models.ForeignKey(
        Department,
        verbose_name=_("Департамент назначения"),
        on_delete=models.SET_NULL,
        null=True, blank=True # Может быть общим для группы
    )
    employee = models.ForeignKey(
        User,
        verbose_name=_("Принимающий сотрудник (основной)"),
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='group_visits_responsible_for',
        limit_choices_to={'is_staff': True} # Пример ограничения
    )
    purpose = models.ForeignKey(
        VisitPurpose,
        verbose_name=_("Основная цель визита группы"),
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    purpose_other_text = models.TextField(
        _("Уточнение цели (если 'Другое')"),
        blank=True, null=True
    )
    expected_entry_time = models.DateTimeField(
        _("Планируемое время входа группы"),
        null=True, blank=True
    )
    # Можно добавить поле для ожидаемого времени выхода группы
    # expected_exit_time = models.DateTimeField(...)

    registered_by = models.ForeignKey(
        User,
        verbose_name=_("Зарегистрировал группу"),
        on_delete=models.SET_NULL,
        null=True,
        related_name='registered_visit_groups'
    )
    registration_time = models.DateTimeField(
        _("Время регистрации группы"),
        default=timezone.now
    )
    # Общий статус для группы, если нужен (например, если вся группа вошла/вышла)
    # group_status = models.CharField(...)

    notes = models.TextField(_("Примечания по группе"), blank=True, null=True)

    class Meta:
        verbose_name = _("Групповой визит")
        verbose_name_plural = _("Групповые визиты")
        ordering = ['-registration_time']

    def __str__(self):
        return self.group_name or f"Группа от {self.registration_time.strftime('%Y-%m-%d %H:%M')}"
