# Используем официальный образ Python
FROM python:3.13-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=visitor_system.settings_docker 

ENV POETRY_VERSION=1.7.1 
ENV POETRY_HOME="/opt/poetry" 
ENV POETRY_VIRTUALENVS_CREATE=false 
ENV PATH="${POETRY_HOME}/bin:${PATH}"

# Устанавливаем основную рабочую директорию для приложения
WORKDIR /app

# Устанавливаем зависимости системы, если они нужны (например, для psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    gcc \
    libpq-dev \
    postgresql-client \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Устанавливаем poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION} --yes
# Копируем файлы Poetry и устанавливаем зависимости
COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-interaction --no-ansi --no-dev --no-root

# Создаем пользователя, чтобы не запускать приложение от root
RUN groupadd -r appuser && useradd --no-create-home -r -g appuser appuser

# Копируем код Django проекта (содержимое d:\university_visitor_system\visitor_system\) в /app/
COPY ./visitor_system/ /app/

# Создаем необходимые директории и устанавливаем права
RUN mkdir -p /app/logs /app/media /app/staticfiles && \
    chown -R appuser:appuser /app

# Собираем статические файлы
RUN poetry run python manage.py collectstatic --noinput --settings=visitor_system.settings_docker

# Копируем entrypoint скрипт и делаем его исполняемым
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Открываем порт, на котором будет работать Gunicorn
EXPOSE 8000

# Устанавливаем пользователя для запуска
USER appuser
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
# Открываем порт, на котором будет работать Gunicorn
EXPOSE 8000

# Запускаем Gunicorn
# Пользователь и группа 'appuser' должны быть созданы, если вы хотите запускать не от root
RUN groupadd -r appuser && useradd --no-create-home -r -g appuser appuser
COPY --chown=appuser:appuser ./visitor_system/ /app/
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

ENTRYPOINT ["entrypoint.sh"]

CMD ["poetry", "run", "gunicorn", "visitor_system.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--log-file", "/app/logs/gunicorn.log"]