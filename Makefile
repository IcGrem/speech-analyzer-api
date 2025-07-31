.PHONY: help build up down logs dev test clean

# Переменные
COMPOSE_FILE = docker-compose.yml
COMPOSE_DEV_FILE = docker-compose.dev.yml
DOCKER_COMPOSE = sudo docker-compose

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Собрать Docker образы
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) build

up: ## Запустить продакшн окружение
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d

down: ## Остановить все контейнеры
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) down

dev: ## Запустить режим разработки
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) up -d

dev-build: ## Собрать и запустить режим разработки
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) build
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) up -d

logs: ## Показать логи приложения
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) logs -f app

dev-logs: ## Показать логи в режиме разработки
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) logs -f app

migrate: ## Запустить миграции
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) exec app alembic upgrade head

dev-migrate: ## Запустить миграции в режиме разработки
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) exec app alembic upgrade head

test: ## Запустить тесты
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) exec app pytest

test-cov: ## Запустить тесты с покрытием
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) exec app pytest --cov=app --cov-report=html

shell: ## Открыть shell в контейнере приложения
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) exec app bash

dev-shell: ## Открыть shell в контейнере разработки
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) exec app bash

clean: ## Очистить все контейнеры и образы
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down -v --rmi all
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) down -v --rmi all
	sudo docker system prune -f

setup: ## Первоначальная настройка
	@chmod +x scripts/docker-setup.sh
	./scripts/docker-setup.sh

dev-setup: ## Настройка режима разработки
	@chmod +x scripts/docker-dev.sh
	./scripts/docker-dev.sh

status: ## Показать статус контейнеров
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) ps
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) ps

restart: ## Перезапустить приложение
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) restart app

dev-restart: ## Перезапустить приложение в режиме разработки
	$(DOCKER_COMPOSE) -f $(COMPOSE_DEV_FILE) restart app

# Дополнительные команды для работы с sudo
fix-permissions: ## Исправить права доступа к файлам
	sudo chown -R $(USER):$(USER) uploads/
	sudo chown -R $(USER):$(USER) ./

setup-alias: ## Настроить алиас для удобства
	@echo "Добавление алиаса в ~/.bashrc..."
	@if ! grep -q "alias dcp=" ~/.bashrc; then \
		echo "alias dcp='sudo docker-compose'" >> ~/.bashrc; \
		echo "✅ Алиас добавлен. Выполните: source ~/.bashrc"; \
	else \
		echo "✅ Алиас уже существует"; \
	fi 