#!/bin/bash

# Ticket System - Быстрый старт

echo "🎫 Ticket System - Инициализация"
echo "================================="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не установлен. Пожалуйста, установите Python 3.8+"
    exit 1
fi

echo "✅ Python найден: $(python3 --version)"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация окружения
echo "🔄 Активация окружения..."
source venv/bin/activate

# Установка зависимостей
echo "📥 Установка зависимостей..."
pip install -q -r requirements.txt

# Применение миграций
echo "🗄️  Применение миграций..."
python manage.py migrate --noinput

# Инициализация БД
echo "⚙️  Инициализация данных..."
python init_db.py

# Сбор статических файлов
echo "📁 Сбор статических файлов..."
python manage.py collectstatic --noinput

# Информация о доступе
echo ""
echo "✨ Инициализация завершена!"
echo ""
echo "📊 Информация для входа:"
echo "   Логин: admin"
echo "   Пароль: admin123"
echo ""
echo "🚀 Для запуска сервера выполните:"
echo "   python manage.py runserver"
echo ""
echo "🔗 Приложение будет доступно по адресу:"
echo "   http://localhost:8000"
echo ""
echo "👤 Админка:"
echo "   http://localhost:8000/admin/"
echo ""
