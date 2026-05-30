FROM python:3.12-slim

WORKDIR /app

# Устанавливаем системные зависимости для сборки пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY pyproject.toml .

# Устанавливаем зависимости через pip (uv не обязателен в контейнере)
# Флаг --no-cache-dir уменьшает размер образа
RUN pip install --no-cache-dir .

# Копируем исходный код
COPY . .

# Открываем порт для FastAPI
EXPOSE 8000

# Запуск приложения
# Убедись, что 'main:app' соответствует твоей структуре (файл main.py, объект app)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]