# d:\university_visitor_system\Dockerfile
FROM python:3.13-slim as base

# Аргументы, которые можно передать во время сборки
ARG DJANGO_SETTINGS_MODULE=visitor_system.settings_docker

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_VERSION=1.7.1 
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_CREATE=false 
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE} 

# Установка системных зависимостей
# build-essential и libpq-dev могут понадобиться для psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

# Установка зависимостей без использования poetry.lock
# Вместо использования файлов poetry.lock и pyproject.toml,
# установим необходимые зависимости напрямую
RUN pip install django>=5.0.0 django-allauth>=65.7.0 requests>=2.32.3 pillow>=11.2.1 \
    python-dotenv>=1.1.0 pyopenssl>=25.0.0 werkzeug>=3.1.3 django-extensions>=4.1 \
    django-select2>=8.4.0 django-filter>=25.1 openpyxl>=3.1.5 celery>=5.5.1 \
    redis>=5.2.1 django-redis>=5.4.0 psycopg2-binary>=2.9.10 pyngrok>=7.2.5 \
    gunicorn>=23.0.0 django-pwa>=2.0.1 django-widget-tweaks>=1.5.0 faker>=37.3.0

# Копируем остальной код приложения
COPY . .

# Special handling for entrypoint.sh - make sure it exists
COPY entrypoint.sh /app/entrypoint.sh

# Make sure entrypoint.sh is executable
RUN chmod +x /app/entrypoint.sh
RUN ls -la /app | grep entrypoint

# Debug information
RUN ls -la /app
RUN echo "DJANGO_SETTINGS_MODULE is: $DJANGO_SETTINGS_MODULE"

# Проверка наличия Django
RUN python -c "import django; print(f'Django version: {django.__version__}')"
RUN python -c "import sys; print(f'Python path: {sys.path}')"

# Проверка настроек базы данных
RUN echo "Checking database settings..." && \
    python -c "import os; print(f'Database host: {os.environ.get(\"POSTGRES_HOST\", \"not set\")}')"

# НЕ собираем статические файлы на этапе сборки - это будет делать entrypoint.sh
# Это позволит избежать ошибок с подключением к базе данных во время сборки

# Порт, на котором будет работать Gunicorn
EXPOSE 8000

# Используем entrypoint.sh для инициализации и запуска приложения
ENTRYPOINT ["/app/entrypoint.sh"]
