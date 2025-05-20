# Используем официальный образ Python
FROM python:3.13-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=visitor_system.settings_docker 

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем Poetry
ENV POETRY_VERSION=1.7.1
RUN pip install "poetry==$POETRY_VERSION"

# Конфигурируем Poetry так, чтобы он не создавал виртуальное окружение внутри проекта,
# так как Docker сам по себе обеспечивает изоляцию.
RUN poetry config virtualenvs.create false

# Устанавливаем зависимости системы, если они нужны (например, для psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Копируем файлы Poetry и устанавливаем зависимости
# Копируем только эти файлы для кэширования слоя зависимостей
COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-interaction --no-ansi --no-dev --no-root

# Копируем весь проект в контейнер
COPY . /app/

# DEBUG: Confirm current working directory and list contents of /app
RUN pwd
RUN ls -la /app

# Собираем статические файлы
# Эти переменные окружения могут понадобиться для collectstatic, если DEBUG=False
# Убедитесь, что они доступны во время сборки, если это необходимо,
# или настройте settings_docker.py так, чтобы он мог работать без них для collectstatic.
# RUN SECRET_KEY="dummy-for-collectstatic" DJANGO_ALLOWED_HOSTS="localhost" python manage.py collectstatic --noinput
RUN poetry run python manage.py collectstatic --noinput --settings=visitor_system.settings_docker

# Открываем порт, на котором будет работать Gunicorn
EXPOSE 8000

# Запускаем Gunicorn
# Пользователь и группа 'appuser' должны быть созданы, если вы хотите запускать не от root
# RUN groupadd -r appuser && useradd -r -g appuser appuser
# USER appuser # Раскомментируйте, если создаете и используете непривилегированного пользователя

CMD ["poetry", "run", "gunicorn", "visitor_system.wsgi:application", "--bind", "0.0.0.0:8000"]
