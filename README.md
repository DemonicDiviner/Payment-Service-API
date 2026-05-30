# Payment Service API

Учебный проект: REST API для управления пользователями, счетами и обработкой платежей.  
Разработан в рамках подготовки к стажировке в «Группа Астра».

##  Особенности

- JWT-аутентификация с разграничением ролей (User / Admin)
- Обработка вебхуков от платёжной системы с проверкой цифровой подписи (SHA256)
- Идемпотентность транзакций (защита от двойного списания)
- Асинхронная работа с PostgreSQL через SQLAlchemy 2.0
- Полная контейнеризация через Docker & Docker Compose
- Миграции базы данных с помощью Alembic

##  Технологический стек

| Категория | Технологии |
|-----------|-----------|
| Язык | Python 3.12 |
| Фреймворк | FastAPI |
| База данных | PostgreSQL + SQLAlchemy (async) |
| Миграции | Alembic |
| Аутентификация | JWT (PyJWT) |
| Валидация | Pydantic |
| Контейнеризация | Docker, Docker Compose |
| Менеджер пакетов | UV / pip |

##  Быстрый старт (Docker)

### 1. Клонирование и настройка

```bash
# Клонируй репозиторий
git clone <твой-репозиторий>
cd payment-service

# Создай файл .env (если нет)
cp .env.example .env  # или создай вручную

2. Запуск через Docker Compose

# Запуск контейнеров
docker compose up --build

# Применение миграций (в отдельном терминале)
docker compose exec web alembic upgrade head

3. Проверка работы
Приложение: http://localhost:8000
Swagger UI (документация API): http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

Тестовые учетные данные
Роль          | Email           | Пароль   | Доступ
Пользователь   user@example.com   user123    /user/*, /auth/login
Админ          admin@example.com  admin123   /admin/*, управление пользователями

Основные эндпоинты
Аутентификация
Метод  Эндпоинт      Описание
POST   /auth/login   Получение JWT-токена (OAuth2 password flow)

Пользователь (требует токен)
Метод    Эндпоинт         Описание
GET      /user/me         Профиль текущего пользователя
GET      /user/accounts   Список счетов пользователя
GET      /user/payments   История платежей пользователя

Платежи
Метод  Эндпоинт          Описание
POST   /webhook/payment  Обработка входящего вебхука от платёжной системы

Админ-панель (требует токен с ролью admin)
Метод   Эндпоинт           Описание
GET     /admin/me          Профиль администратора
GET     /admin/users       Список всех пользователей с их счетами
POST    /admin/users       Создание нового пользователя
PUT     /admin/users/{id}  Обновление данных пользователя
DELETE  /admin/users/{id}  Удаление пользователя

Пример запроса: авторизация
curl -X POST 'http://localhost:8000/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=user@example.com&password=user123'

Ответ:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

Что дальше? (План развития)
- Добавить юнит-тесты (pytest + httpx)
- Реализовать refresh-токены для долгосрочных сессий
- Добавить логирование и мониторинг (structlog + Prometheus)
- Настроить CI/CD пайплайн (GitHub Actions)

Примечание: Проект создан в учебных целях.
