import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticket_system.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import Priority, Status

# Создаем суперпользователя
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@test.local', 'admin123')
    print('✅ Суперпользователь admin создан!')
    print('   Логин: admin')
    print('   Пароль: admin123')
else:
    print('ℹ️  Суперпользователь admin уже существует')

# Создаем приоритеты по умолчанию
priorities_data = [
    ('low', 'Низкий', '#17a2b8'),
    ('medium', 'Средний', '#ffc107'),
    ('high', 'Высокий', '#fd7e14'),
    ('critical', 'Критический', '#dc3545'),
]

for name, display, color in priorities_data:
    Priority.objects.get_or_create(name=name, defaults={'color': color})
print('✅ Приоритеты созданы/обновлены')

# Создаем статусы по умолчанию
statuses_data = [
    ('open', 'Открыт', '#0066cc', False),
    ('in_progress', 'В работе', '#0052a3', False),
    ('waiting', 'Ожидание', '#6c757d', False),
    ('resolved', 'Решен', '#28a745', False),
    ('closed', 'Закрыт', '#495057', True),
    ('reopened', 'Переоткрыт', '#ff6b6b', False),
]

for name, display, color, is_final in statuses_data:
    Status.objects.get_or_create(name=name, defaults={'color': color, 'is_final': is_final})
print('✅ Статусы созданы/обновлены')

print('\n🎉 Инициализация завершена!')
