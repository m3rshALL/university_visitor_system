# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE visitor_system.settings_docker # Указываем на Docker-специфичные настройки

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости системы, если они нужны (например, для psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей и устанавливаем их
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект в контейнер
COPY . /app/

# Собираем статические файлы
# Эти переменные окружения могут понадобиться для collectstatic, если DEBUG=False
# Убедитесь, что они доступны во время сборки, если это необходимо,
# или настройте settings_docker.py так, чтобы он мог работать без них для collectstatic.
# RUN SECRET_KEY="dummy-for-collectstatic" DJANGO_ALLOWED_HOSTS="localhost" python manage.py collectstatic --noinput
RUN python manage.py collectstatic --noinput --settings=visitor_system.settings_docker

# Открываем порт, на котором будет работать Gunicorn
EXPOSE 8000

# Запускаем Gunicorn
# Пользователь и группа 'appuser' должны быть созданы, если вы хотите запускать не от root
# RUN addgroup --system appuser && adduser --system --ingroup appuser appuser
# USER appuser

CMD ["gunicorn", "visitor_system.wsgi:application", "--bind", "0.0.0.0:8000"]
