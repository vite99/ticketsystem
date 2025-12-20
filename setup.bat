@echo off
REM Ticket System - Быстрый старт (Windows)

echo.
echo 🎫 Ticket System - Инициализация
echo =================================
echo.

REM Проверка Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python не установлен. Пожалуйста, установите Python 3.8+
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✅ %PYTHON_VERSION% найден

REM Создание виртуального окружения
if not exist "venv\" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
)

REM Активация окружения
echo 🔄 Активация окружения...
call venv\Scripts\activate.bat

REM Установка зависимостей
echo 📥 Установка зависимостей...
pip install -q -r requirements.txt

REM Применение миграций
echo 🗄️  Применение миграций...
python manage.py migrate --noinput

REM Инициализация БД
echo ⚙️  Инициализация данных...
python init_db.py

REM Сбор статических файлов
echo 📁 Сбор статических файлов...
python manage.py collectstatic --noinput

REM Информация о доступе
echo.
echo ✨ Инициализация завершена!
echo.
echo 📊 Информация для входа:
echo    Логин: admin
echo    Пароль: admin123
echo.
echo 🚀 Для запуска сервера выполните:
echo    python manage.py runserver
echo.
echo 🔗 Приложение будет доступно по адресу:
echo    http://localhost:8000
echo.
echo 👤 Админка:
echo    http://localhost:8000/admin/
echo.
pause
