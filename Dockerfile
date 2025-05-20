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

RUN pip install "poetry==$POETRY_VERSION"
# Устанавливаем зависимости системы, если они нужны (например, для psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION} --yes
# Копируем файлы Poetry и устанавливаем зависимости
# Копируем только эти файлы для кэширования слоя зависимостей
COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-interaction --no-ansi --no-dev --no-root

# Копируем код Django проекта (содержимое d:\university_visitor_system\visitor_system\) в /app/
# Теперь manage.py будет в /app/manage.py
# А каталог приложения visitor_system (с settings.py) будет в /app/visitor_system/
COPY ./visitor_system/ /app/

# DEBUG: Confirm current working directory and list its contents
RUN pwd
RUN ls -la /app/


# Собираем статические файлы
# Эти переменные окружения могут понадобиться для collectstatic, если DEBUG=False
# Убедитесь, что они доступны во время сборки, если это необходимо,
# или настройте settings_docker.py так, чтобы он мог работать без них для collectstatic.
# RUN SECRET_KEY="dummy-for-collectstatic" DJANGO_ALLOWED_HOSTS="localhost" python manage.py collectstatic --noinput
RUN poetry run python manage.py collectstatic --noinput --settings=visitor_system.settings_docker

RUN mkdir -p /app/logs

# Копируем entrypoint скрипт и делаем его исполняемым
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
USER appuser 

CMD ["poetry", "run", "gunicorn", "visitor_system.wsgi:application", "--bind", "0.0.0.0:8000"]