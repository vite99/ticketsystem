# 🚀 Инструкции по развертыванию Ticket System

## Быстрый старт (локальная разработка)

### 1. Подготовка окружения

```bash
# Перейти в папку проекта
cd диплом

# Активировать виртуальное окружение
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### 2. Инициализация БД

```bash
# Применить миграции
python manage.py migrate

# Создать администратора (если нужен новый)
python init_db.py  # или вручную:
python manage.py createsuperuser
```

### 3. Запуск сервера

```bash
# Dev сервер (http://localhost:8000)
python manage.py runserver

# Админка доступна по: http://localhost:8000/admin/
# Логин: admin / Пароль: admin123
```

---

## Развертывание на Production (Heroku)

### Требования
- Git
- Heroku CLI установлена и настроена

### Шаги

```bash
# 1. Создать Procfile в корне проекта
echo "web: gunicorn ticket_system.wsgi" > Procfile

# 2. Создать app на Heroku
heroku create ticket-system-app

# 3. Установить переменные окружения
heroku config:set SECRET_KEY="your-secret-key-here"
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS="ticket-system-app.herokuapp.com"
heroku config:set DATABASE_URL="postgresql://..."

# 4. Завести PostgreSQL базу данных
heroku addons:create heroku-postgresql:hobby-dev

# 5. Push на Heroku
git push heroku main

# 6. Запустить миграции на Heroku
heroku run python manage.py migrate

# 7. Создать супер-юзера
heroku run python manage.py createsuperuser
```

---

## Развертывание с помощью Docker

### 1. Dockerfile

Создать `Dockerfile` в корне проекта:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установить системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копировать requirements и установить зависимости
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копировать код приложения
COPY . .

# Собрать static файлы
RUN python manage.py collectstatic --noinput

# Expose порт
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "ticket_system.wsgi:application"]
```

### 2. docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ticket_db
      POSTGRES_USER: ticket_user
      POSTGRES_PASSWORD: secure_password_here
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build: .
    command: gunicorn ticket_system.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - SECRET_KEY=your-secret-key-here
      - DATABASE_URL=postgresql://ticket_user:secure_password_here@db:5432/ticket_db
    depends_on:
      - db

volumes:
  postgres_data:
```

### 3. Сборка и запуск

```bash
# Собрать образы
docker-compose build

# Запустить контейнеры
docker-compose up

# Запустить миграции (в отдельном терминале)
docker-compose exec web python manage.py migrate

# Создать суперпользователя
docker-compose exec web python manage.py createsuperuser
```

Приложение будет доступно на `http://localhost:8000`

---

## Развертывание на Ubuntu 20.04 (VPS)

### 1. Подготовка сервера

```bash
# Обновить систему
sudo apt update && sudo apt upgrade -y

# Установить зависимости
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib nginx supervisor git

# Создать пользователя для приложения
sudo useradd -m -s /bin/bash ticketapp

# Переключиться на этого пользователя
sudo su - ticketapp
```

### 2. Развернуть приложение

```bash
# Клонировать репозиторий
git clone <ваш-репозиторий> ~/ticket_system
cd ~/ticket_system/диплом

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
pip install gunicorn

# Применить миграции
python manage.py migrate

# Собрать static файлы
python manage.py collectstatic --noinput
```

### 3. Настроить Gunicorn

Создать файл `/etc/systemd/system/ticket_gunicorn.service`:

```ini
[Unit]
Description=Gunicorn daemon for ticket_system
After=network.target

[Service]
User=ticketapp
Group=www-data
WorkingDirectory=/home/ticketapp/ticket_system/диплом
ExecStart=/home/ticketapp/ticket_system/диплом/venv/bin/gunicorn \
          --workers 3 \
          --bind unix:/home/ticketapp/ticket_system/диплом/gunicorn.sock \
          ticket_system.wsgi:application

[Install]
WantedBy=multi-user.target
```

Запустить сервис:

```bash
sudo systemctl start ticket_gunicorn
sudo systemctl enable ticket_gunicorn
```

### 4. Настроить Nginx

Создать конфиг `/etc/nginx/sites-available/ticket_system`:

```nginx
upstream ticket_gunicorn {
    server unix:/home/ticketapp/ticket_system/диплом/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name your_domain.com;
    client_max_body_size 50M;

    location /static/ {
        alias /home/ticketapp/ticket_system/диплом/staticfiles/;
    }

    location /media/ {
        alias /home/ticketapp/ticket_system/диплом/media/;
    }

    location / {
        proxy_pass http://ticket_gunicorn;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Включить конфиг:

```bash
sudo ln -s /etc/nginx/sites-available/ticket_system /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### 5. Настроить SSL с Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com
```

---

## Переменные окружения (`.env`)

Установить перед развертыванием:

```env
# Django
SECRET_KEY=your-very-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (если использовать PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/ticket_db

# Email (SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

---

## Резервное копирование БД

### PostgreSQL

```bash
# Экспорт
pg_dump -U username -d ticket_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Импорт
psql -U username -d ticket_db < backup_file.sql
```

### SQLite

```bash
# Просто скопировать файл
cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)
```

---

## Мониторинг и логирование

### Просмотр логов

```bash
# Gunicorn
sudo journalctl -u ticket_gunicorn -f

# Nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Django (в приложении)
python manage.py tail_log
```

### Настройка логирования в settings.py

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'ticket_system.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
```

---

## Обновление приложения

```bash
# Получить новый код
git pull origin main

# Установить новые зависимости
pip install -r requirements.txt

# Применить новые миграции
python manage.py migrate

# Собрать static файлы
python manage.py collectstatic --noinput

# Перезапустить сервис
sudo systemctl restart ticket_gunicorn
sudo systemctl restart nginx
```

---

## Удаление и очистка

```bash
# Удалить все данные и начать с нуля
python manage.py flush

# Удалить БД
rm db.sqlite3

# Очистить static файлы
rm -rf staticfiles/
```

---

## Решение проблем

### Ошибка 502 Bad Gateway

```bash
# Проверить статус gunicorn
sudo systemctl status ticket_gunicorn

# Проверить логи
sudo journalctl -u ticket_gunicorn -n 50
```

### Ошибка "DEBUG must be False in production"

```python
# settings.py
DEBUG = os.getenv('DEBUG', 'False') == 'True'
```

### Проблемы с статическими файлами

```bash
# Собрать static файлы
python manage.py collectstatic --clear --noinput
```

---

**Дата обновления:** 20.12.2025  
**Версия:** 1.0.0
