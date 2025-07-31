#!/bin/bash

# Скрипт для настройки Docker без sudo

set -e

echo "🔧 Настройка Docker для работы без sudo..."

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен."
    exit 1
fi

# Проверка прав sudo
if ! sudo -n true 2>/dev/null; then
    echo "🔐 Требуются права sudo для настройки"
    echo "Пожалуйста, введите пароль sudo:"
    sudo true
fi

# Создание группы docker если её нет
if ! getent group docker > /dev/null 2>&1; then
    echo "📦 Создание группы docker..."
    sudo groupadd docker
fi

# Добавление текущего пользователя в группу docker
echo "👤 Добавление пользователя $(whoami) в группу docker..."
sudo usermod -aG docker $(whoami)

# Перезапуск службы Docker
echo "🔄 Перезапуск службы Docker..."
sudo systemctl restart docker

echo "✅ Настройка завершена!"
echo ""
echo "⚠️  ВАЖНО: Выйдите из системы и войдите снова, чтобы изменения вступили в силу."
echo "   Или выполните: newgrp docker"
echo ""
echo "💡 После перезахода вы сможете использовать Docker без sudo:"
echo "   docker ps"
echo "   docker-compose up"
echo ""
echo "🔧 Для применения изменений без перезахода выполните:"
echo "   newgrp docker" 