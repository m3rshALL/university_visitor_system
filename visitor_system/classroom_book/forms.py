from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Classroom, KeyBooking


class KeyBookingForm(forms.ModelForm):
    """Форма бронирования ключа аудитории"""

    # Переопределяем поле для выпадающего списка аудиторий
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Аудитория'
    )

    # Используем HTML5 datetime-local input
    start_time = forms.DateTimeField(
        label='Время начала',
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'},
            format='%Y-%m-%dT%H:%M'
        )
    )

    end_time = forms.DateTimeField(
        label='Время окончания',
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'},
            format='%Y-%m-%dT%H:%M'
        )
    )

    class Meta:
        model = KeyBooking
        fields = ['classroom', 'start_time', 'end_time', 'purpose']
        widgets = {
            'purpose': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(KeyBookingForm, self).__init__(*args, **kwargs)

        # Устанавливаем значения по умолчанию для времени
        if not self.is_bound:  # Если форма не была отправлена
            now = timezone.localtime()
            rounded_hour = now.replace(minute=0, second=0, microsecond=0)
            if now.minute > 0:
                rounded_hour += timedelta(hours=1)

            self.fields['start_time'].initial = rounded_hour
            self.fields['end_time'].initial = rounded_hour + timedelta(hours=1)

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        classroom = cleaned_data.get('classroom')

        if start_time and end_time and classroom:
            # Проверка, что время начала не в прошлом
            now = timezone.now()
            if start_time < now:
                self.add_error('start_time', 'Время начала не может быть в прошлом')

            # Проверка, что время окончания после времени начала
            if end_time <= start_time:
                self.add_error('end_time', 'Время окончания должно быть позже '
                                   'времени начала')

            # Проверка, что бронирование не превышает 8 часов
            max_duration = timedelta(hours=8)
            if end_time - start_time > max_duration:
                self.add_error('end_time', 'Максимальная продолжительность '
                                   'бронирования - 8 часов')

            # Проверка доступности аудитории
            if not classroom.is_available(start_time, end_time):
                self.add_error('classroom', 'Аудитория уже забронирована '
                                   'на указанное время')

            # Проверка наличия доступного ключа
            available_key = classroom.get_available_key()
            if not available_key:
                self.add_error('classroom', 'Для этой аудитории нет '
                               'доступных ключей')

        return cleaned_data


class QuickBookingConfirmForm(forms.Form):
    """Форма для быстрого подтверждения бронирования по QR-коду"""
    confirm = forms.BooleanField(
        required=True,
        initial=True,
        widget=forms.HiddenInput()
    )
