# Базовый образ (убедитесь, что версия Python совпадает с pyproject.toml)
FROM python:3.13-slim

# Установка переменных окружения
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_VERSION=1.5.1 

# Рабочая директория
WORKDIR /app

# Установка зависимостей системы (если нужны)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \ # Нужен для установки Poetry
    # ... другие системные зависимости
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION}
ENV PATH="/root/.local/bin:$PATH" 

# Настройка Poetry, чтобы не создавать виртуальное окружение внутри контейнера
RUN poetry config virtualenvs.create false

# Копирование файлов зависимостей
# Копируем сначала их, чтобы Docker мог кэшировать слой установки зависимостей
COPY pyproject.toml poetry.lock* /app/

# Установка зависимостей проекта (без dev-зависимостей)
# --no-interaction: не задавать интерактивных вопросов
# --no-ansi: для более чистого вывода в логах
# --no-root: не устанавливать сам проект как пакет (если код копируется позже)
# Если ваш проект должен быть установлен как пакет, уберите --no-root
RUN poetry install --no-dev --no-interaction --no-ansi

# Копирование всего проекта
COPY . /app/

# Порт, который будет слушать Gunicorn
EXPOSE 8000

# Пользователь (рекомендуется не root)
# RUN addgroup --system app && adduser --system --group app
# USER app

# Запуск (через entrypoint скрипт или напрямую)
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Если без entrypoint.sh:
# CMD ["poetry", "run", "gunicorn", "--bind", "0.0.0.0:8000", "your_project_name.wsgi:application"]