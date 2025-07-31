#!/bin/bash

# Скрипт для настройки Docker окружения

set -e

echo "🚀 Настройка Docker окружения для Speech Analyzer API"

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

# Проверка наличия Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
    exit 1
fi

# Проверка прав sudo
if ! sudo -n true 2>/dev/null; then
    echo "🔐 Требуются права sudo для работы с Docker"
    echo "Пожалуйста, введите пароль sudo:"
    sudo true
fi

# Создание директории для загрузок
echo "📁 Создание директории uploads..."
mkdir -p uploads
sudo chown -R $USER:$USER uploads

# Создание .env файла если его нет
if [ ! -f .env ]; then
    echo "📝 Создание .env файла..."
    cp env.example .env
    echo "✅ .env файл создан. Отредактируйте его при необходимости."
fi

# Сборка и запуск контейнеров
echo "🔨 Сборка Docker образов..."
sudo docker-compose build

echo "🚀 Запуск сервисов..."
sudo docker-compose up -d

# Ожидание готовности базы данных
echo "⏳ Ожидание готовности базы данных..."
sleep 10

# Запуск миграций
echo "🗄️ Запуск миграций базы данных..."
sudo docker-compose exec app alembic upgrade head

echo "✅ Настройка завершена!"
echo ""
echo "🌐 API доступен по адресу: http://localhost"
echo ""
echo "📋 Полезные команды:"
echo "  sudo docker-compose logs -f app     # Просмотр логов приложения"
echo "  sudo docker-compose down            # Остановка всех сервисов"
echo "  sudo docker-compose restart app     # Перезапуск приложения"
echo ""
echo "💡 Для удобства добавьте алиас в ~/.bashrc:"
echo "   alias dcp='sudo docker-compose'" 