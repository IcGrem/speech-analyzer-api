# Speech Analyzer API

API для анализа речи с использованием FastAPI и архитектуры "чистый код".

## Структура проекта

```
speech-analyzer-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── analysis.py
│   │       │   └── health.py
│   │       └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   ├── models/
│   │   └── analysis.py
│   ├── schemas/
│   │   ├── analysis.py
│   │   └── health.py
│   ├── services/
│   │   ├── analysis_service.py
│   │   ├── health_service.py
│   │   └── speech_processor.py
│   └── main.py
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── tests/
│   ├── conftest.py
│   ├── test_analysis.py
│   └── test_health.py
├── scripts/
│   ├── docker-setup.sh
│   ├── docker-dev.sh
│   └── setup-docker-user.sh
├── requirements.txt
├── pyproject.toml
├── alembic.ini
├── env.example
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── nginx.conf
├── .dockerignore
└── Makefile
```

## Быстрый старт с Docker

### Вариант 1: С sudo (рекомендуется для серверов)

#### Продакшн окружение

1. Клонируйте репозиторий
2. Запустите автоматическую настройку:
   ```bash
   make setup
   ```
   
   Или вручную:
   ```bash
   chmod +x scripts/docker-setup.sh
   ./scripts/docker-setup.sh
   ```

3. API будет доступен по адресу: http://localhost

#### Режим разработки

1. Запустите режим разработки:
   ```bash
   make dev-setup
   ```
   
   Или вручную:
   ```bash
   chmod +x scripts/docker-dev.sh
   ./scripts/docker-dev.sh
   ```

2. API будет доступен по адресу: http://localhost:8000
3. PgAdmin доступен по адресу: http://localhost:5050

### Вариант 2: Без sudo (для локальной разработки)

1. Настройте Docker для работы без sudo:
   ```bash
   chmod +x scripts/setup-docker-user.sh
   ./scripts/setup-docker-user.sh
   ```

2. Выйдите из системы и войдите снова (или выполните `newgrp docker`)

3. Теперь можно использовать команды без sudo:
   ```bash
   make setup
   make dev-setup
   ```

## Ручная установка (без Docker)

1. Клонируйте репозиторий
2. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # или
   venv\Scripts\activate  # Windows
   ```

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Скопируйте файл окружения:
   ```bash
   cp env.example .env
   ```

5. Настройте переменные окружения в `.env`

6. Запустите миграции:
   ```bash
   alembic upgrade head
   ```

7. Запустите сервер:
   ```bash
   uvicorn app.main:app --reload
   ```

## Docker команды

### Основные команды

```bash
# Показать справку
make help

# Продакшн
make build    # Собрать образы
make up       # Запустить
make down     # Остановить
make logs     # Показать логи

# Разработка
make dev      # Запустить режим разработки
make dev-logs # Логи разработки
make dev-shell # Shell в контейнере

# Миграции
make migrate      # Продакшн миграции
make dev-migrate  # Миграции разработки

# Тестирование
make test     # Запустить тесты
make test-cov # Тесты с покрытием

# Очистка
make clean    # Очистить все контейнеры и образы

# Дополнительные команды для sudo
make fix-permissions  # Исправить права доступа
make setup-alias      # Настроить алиас dcp
```

### Полезные команды

```bash
# Статус контейнеров
make status

# Перезапуск
make restart      # Продакшн
make dev-restart  # Разработка

# Shell в контейнере
make shell        # Продакшн
make dev-shell    # Разработка
```

### Команды с sudo (если не настроен доступ без sudo)

```bash
# Продакшн
sudo docker-compose up -d
sudo docker-compose down
sudo docker-compose logs -f app

# Разработка
sudo docker-compose -f docker-compose.dev.yml up -d
sudo docker-compose -f docker-compose.dev.yml down
sudo docker-compose -f docker-compose.dev.yml logs -f app

# Алиас для удобства
alias dcp='sudo docker-compose'
dcp up -d
dcp logs -f app
```

## API Endpoints

- `GET /api/v1/health/` - Проверка здоровья приложения
- `POST /api/v1/analysis/` - Создание нового анализа речи
- `GET /api/v1/analysis/` - Получение списка анализов
- `GET /api/v1/analysis/{id}` - Получение конкретного анализа
- `DELETE /api/v1/analysis/{id}` - Удаление анализа

## Тестирование

### С Docker
```bash
make test
```

### Без Docker
```bash
pytest
```

## Линтинг и форматирование

```bash
# Форматирование кода
black app tests

# Сортировка импортов
isort app tests

# Проверка типов
mypy app

# Линтинг
flake8 app tests
```

## Архитектура

Проект следует принципам "чистого кода":

- **Разделение ответственности**: каждый модуль имеет четкую зону ответственности
- **Dependency Injection**: использование FastAPI dependency injection
- **Слоистая архитектура**: API → Services → Models
- **Валидация данных**: использование Pydantic моделей
- **Обработка ошибок**: кастомные исключения
- **Логирование**: централизованное логирование
- **Тестирование**: unit и integration тесты
- **Контейнеризация**: Docker для развертывания

## Docker сервисы

- **app**: FastAPI приложение
- **postgres**: PostgreSQL база данных
- **redis**: Redis кэш
- **nginx**: Nginx прокси сервер
- **pgadmin**: Веб-интерфейс для управления PostgreSQL (только в dev)

## Устранение проблем

### Проблемы с правами доступа

```bash
# Исправить права доступа к файлам
make fix-permissions

# Или вручную
sudo chown -R $USER:$USER uploads/
sudo chown -R $USER:$USER ./
```

### Проблемы с Docker

```bash
# Очистить все контейнеры и образы
make clean

# Перезапустить Docker
sudo systemctl restart docker

# Проверить статус Docker
sudo systemctl status docker
```

### Настройка алиаса для удобства

```bash
# Добавить алиас dcp='sudo docker-compose'
make setup-alias
source ~/.bashrc

# Теперь можно использовать
dcp up -d
dcp logs -f app
```
