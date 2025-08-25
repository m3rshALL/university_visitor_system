import logging
import django_filters
from .models import Visit, Department, Guest
from django.contrib.auth.models import User
from django.db.models import Q # Для сложного поиска по сотруднику
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

class VisitFilter(django_filters.FilterSet):
    # Фильтр по имени гостя (по частичному совпадению, без учета регистра)
    guest_name = django_filters.CharFilter(
        field_name='guest__full_name',
        lookup_expr='icontains',
        label='ФИО гостя содержит'
    )

    # Фильтр по ИИН гостя (можно искать по частичному совпадению)
    guest_iin = django_filters.CharFilter(
        field_name='guest__iin',
        lookup_expr='icontains', # Или 'exact' для точного совпадения
        label='ИИН гостя содержит'
    )

    # Фильтр по сотруднику (поиск по имени, фамилии или email)
    employee_info = django_filters.CharFilter(
        method='filter_by_employee_info', # Используем кастомный метод фильтрации
        label='Сотрудник (ФИО/Email)'
    )

    # Фильтр по департаменту (выпадающий список)
    department = django_filters.ModelChoiceFilter(
        queryset=Department.objects.all(),
        label='Департамент'
    )

    # Фильтр по дате входа (диапазон дат)
    entry_date = django_filters.DateFromToRangeFilter(
        field_name='entry_time__date', # Фильтруем только по дате, без времени
        label='Дата входа (от - до)',
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date'}) # Используем виджет с полями для дат
    )

    # Фильтр по цели визита (по частичному совпадению)
    purpose = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Цель визита содержит'
    )

    

    class Meta:
        model = Visit
        # Указываем поля модели, по которым можно фильтровать напрямую (если не определены выше)
        # В данном случае мы определили все нужные фильтры выше, поэтому fields можно не указывать
        # или указать только те, для которых не нужна кастомная логика
        fields = [] # Или перечислить 'purpose', 'department' и т.д., если не определять их выше

    # Кастомный метод для поиска по сотруднику
    def filter_by_employee_info(self, queryset, value):
        logger.debug("Filtering by employee_info: '%s'", value)
        if value:            
            # Ищем по совпадению в имени, фамилии или email
            qs = queryset.filter(
                Q(employee__first_name__icontains=value) |
                Q(employee__last_name__icontains=value) |
                Q(employee__email__icontains=value)
            )
            logger.debug(
                "Employee filter reduced queryset from %s to %s",
                queryset.count(),
                qs.count(),
            )
            return qs
        return queryset

    # Кастомный метод для фильтрации по статусу
    def filter_by_status(self, queryset, value):
        logger.warning("VisitFilter.filter_by_status called, but history filtering logic is primarily in the view now.")
        if value == 'active':
            return queryset.filter(exit_time__isnull=True)
        elif value == 'exited':
            return queryset.filter(exit_time__isnull=False)
        return queryset