# Docker и PostgreSQL

## Что теперь поддерживается

Проект можно запускать в двух режимах:

- `SQLite` — для простой локальной разработки
- `PostgreSQL` — для Docker и более приближенного к production сценария

Переключение выполняется через переменную:

```text
DB_ENGINE=sqlite
```

или

```text
DB_ENGINE=postgresql
```

## Быстрый запуск в Docker

1. При необходимости скопируйте пример переменных:

```bash
copy .env.docker.example .env.docker
```

или вручную используйте значения из `.env.docker.example`.

2. Запустите проект:

```bash
docker compose up --build
```

3. После запуска приложение будет доступно по адресу:

```text
http://127.0.0.1:8000/
```

## Что поднимает docker-compose

- `db` — PostgreSQL 16
- `web` — Django-приложение

При старте контейнер `web`:

- ждет готовности PostgreSQL
- применяет миграции
- запускает Django на `0.0.0.0:8000`

## Переменные окружения

Основные переменные:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `CORS_ALLOWED_ORIGINS`
- `SITE_URL`
- `DB_ENGINE`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

Пример готового набора лежит в:

```text
.env.docker.example
```

## Volume

Данные сохраняются в Docker volumes:

- `postgres_data` — база PostgreSQL
- `ticket_media` — загруженные файлы
- `ticket_data` — локальные данные приложения, если используешь SQLite внутри контейнера

## Полезные команды

Остановить контейнеры:

```bash
docker compose down
```

Остановить контейнеры и удалить volume:

```bash
docker compose down -v
```

Создать суперпользователя:

```bash
docker compose exec web python manage.py createsuperuser
```

Открыть Django shell:

```bash
docker compose exec web python manage.py shell
```

## Как перейти с SQLite на PostgreSQL

### Вариант для текущего проекта

1. Сохранить данные из SQLite:

```bash
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > data.json
```

2. Запустить Docker с PostgreSQL:

```bash
docker compose up --build
```

3. Загрузить данные уже в PostgreSQL:

```bash
docker compose exec web python manage.py loaddata data.json
```

4. При необходимости перенести папку `media/` отдельно.

## Как вернуться на SQLite

Для локального запуска без PostgreSQL можно использовать:

```text
DB_ENGINE=sqlite
SQLITE_NAME=db.sqlite3
```

Тогда Django снова будет работать на SQLite.

## Замечание

Текущая сборка подходит для дипломного проекта, локальной демонстрации и учебного развёртывания.
Если понадобится production-вариант, следующим шагом лучше делать:

- `Gunicorn`
- `Nginx`
- отдельную сборку статики
- более строгие production-настройки Django
