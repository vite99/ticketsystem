#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticket_system.settings")
django.setup()

from tickets.models import Workstation

# Создание примеров рабочих мест для разных кабинетов
workstations_data = [
    {'room': '101 (IT кабинет)', 'number': 'ПК-1', 'location': 'Левый угол, у окна'},
    {'room': '101 (IT кабинет)', 'number': 'ПК-2', 'location': 'Центр, основной стол'},
    {'room': '101 (IT кабинет)', 'number': 'ПК-3', 'location': 'Правый угол'},
    {'room': '102 (Офис)', 'number': 'ПК-1', 'location': 'Левый край'},
    {'room': '102 (Офис)', 'number': 'ПК-2', 'location': 'Центр'},
    {'room': '103 (Лаборатория)', 'number': 'Рабочее место 1', 'location': 'Стол 1'},
    {'room': '103 (Лаборатория)', 'number': 'Рабочее место 2', 'location': 'Стол 2'},
]

print("Создание рабочих мест...\n")
for data in workstations_data:
    workstation, created = Workstation.objects.get_or_create(
        room=data['room'],
        number=data['number'],
        defaults={'location': data['location']}
    )
    if created:
        print(f'✓ Создано: {data["room"]} - {data["number"]}')
    else:
        print(f'→ Уже существует: {data["room"]} - {data["number"]}')

print(f'\nВсего рабочих мест: {Workstation.objects.count()}')
