#!/bin/bash

# Скрипт для запуска в режиме разработки

set -e

echo "🔧 Запуск в режиме разработки..."

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен."
    exit 1
fi

# Проверка наличия Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен."
    exit 1
fi

# Проверка прав sudo
if ! sudo -n true 2>/dev/null; then
    echo "🔐 Требуются права sudo для работы с Docker"
    echo "Пожалуйста, введите пароль sudo:"
    sudo true
fi

# Создание директории для загрузок
mkdir -p uploads
sudo chown -R $USER:$USER uploads

# Создание .env файла если его нет
if [ ! -f .env ]; then
    echo "📝 Создание .env файла..."
    cp env.example .env
fi

# Остановка продакшн контейнеров если запущены
echo "🛑 Остановка продакшн контейнеров..."
sudo docker-compose down 2>/dev/null || true

# Сборка и запуск в режиме разработки
echo "🔨 Сборка образов для разработки..."
sudo docker-compose -f docker-compose.dev.yml build

echo "🚀 Запуск сервисов в режиме разработки..."
sudo docker-compose -f docker-compose.dev.yml up -d

# Ожидание готовности базы данных
echo "⏳ Ожидание готовности базы данных..."
sleep 10

# Запуск миграций
echo "🗄️ Запуск миграций..."
sudo docker-compose -f docker-compose.dev.yml exec app alembic upgrade head

echo "✅ Режим разработки запущен!"
echo ""
echo "🌐 API доступен по адресу: http://localhost:8000"
echo "📊 PgAdmin доступен по адресу: http://localhost:5050"
echo "   Email: admin@admin.com"
echo "   Password: admin"
echo ""
echo "📋 Полезные команды:"
echo "  sudo docker-compose -f docker-compose.dev.yml logs -f app  # Логи приложения"
echo "  sudo docker-compose -f docker-compose.dev.yml down        # Остановка"
echo "  sudo docker-compose -f docker-compose.dev.yml restart app # Перезапуск"
echo ""
echo "💡 Для удобства добавьте алиас в ~/.bashrc:"
echo "   alias dcp='sudo docker-compose'" 