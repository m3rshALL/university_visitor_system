#!/usr/bin/env python
"""
Скрипт для заполнения базы данных тестовыми аудиториями и ключами
"""

import os
import sys
import django

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from classroom_book.models import Classroom, ClassroomKey

def create_sample_data():
    """Создает тестовые аудитории и ключи"""
    # Создаем аудитории для блоков C1, C2, C3
    classrooms_data = [
        # Блок C1
        {'number': 'C1.1.101', 'building': 'C1', 'floor': 1, 'capacity': 30, 'features': 'Проектор, доска'},
        {'number': 'C1.1.102', 'building': 'C1', 'floor': 1, 'capacity': 25, 'features': 'Интерактивная доска'},
        {'number': 'C1.1.103', 'building': 'C1', 'floor': 1, 'capacity': 20, 'features': 'Семинарская комната'},
        {'number': 'C1.2.201', 'building': 'C1', 'floor': 2, 'capacity': 40, 'features': 'Проектор, кондиционер'},
        {'number': 'C1.2.202', 'building': 'C1', 'floor': 2, 'capacity': 35, 'features': 'Компьютерный класс'},
        {'number': 'C1.2.203', 'building': 'C1', 'floor': 2, 'capacity': 30, 'features': 'Лаборатория'},
        {'number': 'C1.3.301', 'building': 'C1', 'floor': 3, 'capacity': 50, 'features': 'Большая аудитория, микрофоны'},
        {'number': 'C1.3.302', 'building': 'C1', 'floor': 3, 'capacity': 45, 'features': 'Лекционный зал'},
        
        # Блок C2
        {'number': 'C2.1.101', 'building': 'C2', 'floor': 1, 'capacity': 28, 'features': 'Проектор, Smart-доска'},
        {'number': 'C2.1.102', 'building': 'C2', 'floor': 1, 'capacity': 24, 'features': 'Переговорная'},
        {'number': 'C2.1.103', 'building': 'C2', 'floor': 1, 'capacity': 32, 'features': 'Мультимедийный класс'},
        {'number': 'C2.2.201', 'building': 'C2', 'floor': 2, 'capacity': 36, 'features': 'Проектор, система звука'},
        {'number': 'C2.2.202', 'building': 'C2', 'floor': 2, 'capacity': 40, 'features': 'IT-лаборатория'},
        {'number': 'C2.2.203', 'building': 'C2', 'floor': 2, 'capacity': 35, 'features': 'Языковая лаборатория'},
        {'number': 'C2.3.301', 'building': 'C2', 'floor': 3, 'capacity': 60, 'features': 'Актовый зал, сцена'},
        {'number': 'C2.3.302', 'building': 'C2', 'floor': 3, 'capacity': 42, 'features': 'Конференц-зал'},
        
        # Блок C3
        {'number': 'C3.1.101', 'building': 'C3', 'floor': 1, 'capacity': 26, 'features': 'Проектор, флипчарт'},
        {'number': 'C3.1.102', 'building': 'C3', 'floor': 1, 'capacity': 30, 'features': 'Учебная аудитория'},
        {'number': 'C3.1.103', 'building': 'C3', 'floor': 1, 'capacity': 22, 'features': 'Кабинет для практических занятий'},
        {'number': 'C3.2.201', 'building': 'C3', 'floor': 2, 'capacity': 38, 'features': 'Научная лаборатория'},
        {'number': 'C3.2.202', 'building': 'C3', 'floor': 2, 'capacity': 34, 'features': 'Мастерская'},
        {'number': 'C3.2.203', 'building': 'C3', 'floor': 2, 'capacity': 28, 'features': 'Специализированный класс'},
        {'number': 'C3.3.301', 'building': 'C3', 'floor': 3, 'capacity': 55, 'features': 'Большая лекционная аудитория'},
        {'number': 'C3.3.302', 'building': 'C3', 'floor': 3, 'capacity': 48, 'features': 'Многофункциональная аудитория'},
    ]
    
    created_classrooms = 0
    for classroom_data in classrooms_data:
        # Используем полное название аудитории как уникальный номер
        classroom, created = Classroom.objects.get_or_create(
            number=classroom_data['number'],
            defaults=classroom_data
        )
        if created:
            created_classrooms += 1
            print(f"Создана аудитория: {classroom}")
    
    print(f"Создано аудиторий: {created_classrooms}")
    
    # Создаем ключи для каждой аудитории
    created_keys = 0
    for classroom in Classroom.objects.all():
        # Создаем по 2-3 ключа для каждой аудитории
        key_count = 2 if classroom.capacity < 30 else 3
        
        for i in range(1, key_count + 1):
            # Используем короткое имя для ключа: C1-101-01, C2-201-02 и т.д.
            key_number = f"{classroom.building}-{classroom.number.split('.')[-1]}-{i:02d}"
            
            key, created = ClassroomKey.objects.get_or_create(
                key_number=key_number,
                defaults={
                    'classroom': classroom,
                    'is_available': True,
                    'notes': f'Ключ #{i} для аудитории {classroom}'
                }
            )
            if created:
                created_keys += 1
                print(f"Создан ключ: {key}")
    
    print(f"Создано ключей: {created_keys}")
    
    # Выводим статистику
    print("\n=== СТАТИСТИКА ===")
    print(f"Всего аудиторий: {Classroom.objects.count()}")
    print(f"Всего ключей: {ClassroomKey.objects.count()}")
    print(f"Доступных ключей: {ClassroomKey.objects.filter(is_available=True).count()}")
    
    print("\n=== АУДИТОРИИ С КЛЮЧАМИ ===")
    for classroom in Classroom.objects.all():
        keys_count = classroom.keys.count()
        available_keys = classroom.keys.filter(is_available=True).count()
        print(f"{classroom}: {keys_count} ключей ({available_keys} доступно)")

if __name__ == '__main__':
    print("Запуск скрипта создания тестовых данных для системы бронирования аудиторий")
    print("=" * 70)
    
    # Удаляем старые данные (если нужно)
    print("Очистка старых данных...")
    ClassroomKey.objects.all().delete()
    Classroom.objects.all().delete()
    
    # Создаем новые данные
    create_sample_data()
    
    print("\n" + "=" * 70)
    print("Скрипт завершен успешно!")
    print("Создание тестовых данных для системы бронирования аудиторий...")
    create_sample_data()
    print("Готово!")
