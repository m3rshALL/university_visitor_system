# 📸 РЕШЕНИЕ: Фото гостей не появляется в HikCentral

## Диагностика
✅ Гости создаются в HikCentral  
✅ Access levels назначаются  
❌ Фото не загружаются

## Причина
**У модели `Guest` НЕТ поля `photo`!**

Фото хранится в двух местах:
1. `GuestInvitation.guest_photo` - для групповых приглашений
2. **НЕ В Guest!** - нет поля для прямой регистрации

## Решение

### Вариант 1: Добавить поле photo в модель Guest (РЕКОМЕНДУЕТСЯ)

```python
# visitors/models.py

class Guest(models.Model):
    full_name = models.CharField(max_length=255, verbose_name="ФИО гостя")
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Email")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер телефона")
    
    # NEW: Добавляем поле для фото
    photo = models.ImageField(
        upload_to='guest_photos/',
        blank=True,
        null=True,
        verbose_name="Фото гостя"
    )
    
    # Шифрованный ИИН
    iin_encrypted = models.BinaryField(null=True, blank=True, editable=False, verbose_name="Зашифрованный ИИН")
    iin_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True, editable=False, verbose_name="Хэш ИИН (поиск)")
    
    # ... остальные поля
```

**После этого:**

```bash
# Создать миграцию
cd d:\university_visitor_system\visitor_system
poetry run python manage.py makemigrations visitors

# Применить миграцию
poetry run python manage.py migrate visitors
```

### Вариант 2: Использовать GuestInvitation flow (текущее решение)

**Для загрузки фото используйте ТОЛЬКО групповые приглашения:**

1. Создайте приглашение: http://127.0.0.1:8000/visits/group-invitation/
2. Гость заполняет форму с ФОТО: `http://127.0.0.1:8000/visits/invitation/<token>/`
3. После finalize фото загружается из `GuestInvitation.guest_photo`

**НЕ используйте** прямую регистрацию `/visits/register-guest/` - там нет поля для фото!

## Как работает загрузка фото (текущая логика)

### В enroll_face_task есть 3 попытки получить фото:

1. **Из payload** (если передали явно):
   ```python
   image_bytes = payload.get('image_bytes')
   ```

2. **Из Guest.photo** (НЕ РАБОТАЕТ - поля нет):
   ```python
   if not image_bytes and task.guest_id:
       g = Guest.objects.filter(id=task.guest_id).first()
       if g and g.photo and g.photo.path:
           with open(g.photo.path, 'rb') as f:
               image_bytes = f.read()
   ```

3. **Из GuestInvitation.guest_photo** (РАБОТАЕТ):
   ```python
   if not image_bytes:
       inv = GuestInvitation.objects.filter(visit_id=task.visit_id).first()
       if inv and inv.guest_photo and inv.guest_photo.path:
           with open(inv.guest_photo.path, 'rb') as f:
               image_bytes = f.read()
   ```

## Тестирование

### Тест 1: Проверка через групповое приглашение

```bash
# 1. Создайте приглашение в админке или через UI
# 2. Откройте ссылку приглашения
# 3. Заполните форму С ФОТО
# 4. Finalize invitation
# 5. Проверьте HikCentral UI - фото должно быть
```

### Тест 2: Проверка логов загрузки

```powershell
# Смотрим логи Celery worker
cd d:\university_visitor_system\visitor_system
Get-Content celery_hikvision_error.log | Select-String -Pattern "(image|photo|upload_face)" -Context 2,2
```

Должны быть строки:
```
Hik enroll: loaded invitation photo (12345 bytes)
Hik enroll: upload_face start
Hik enroll: upload_face done face_id=...
```

### Тест 3: Проверка HikPersonBinding

```powershell
cd d:\university_visitor_system\visitor_system
poetry run python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev'); import django; django.setup(); from hikvision_integration.models import HikPersonBinding; b = HikPersonBinding.objects.order_by('-id').first(); print(f'Binding {b.id}: person_id={b.person_id}, face_id={b.face_id}')"
```

Если `face_id` пустой - значит фото не загружалось!

## Примеры кода

### Добавление фото в payload (ручной подход)

Если хотите добавить фото в payload перед вызовом enroll_face_task:

```python
# visitors/views.py, в месте создания HikAccessTask

# Пример: если фото загружено через form
photo_file = request.FILES.get('photo')
if photo_file:
    image_bytes = photo_file.read()
else:
    image_bytes = None

payload = {
    'guest_id': guest_id,
    'name': guest_name,
    'image_bytes': image_bytes,  # Добавляем фото
}

task = HikAccessTask.objects.create(
    kind='enroll_face',
    payload=payload,
    status='queued',
    visit_id=visit.id,
    guest_id=guest_id,
)
```

### Обновление формы register_guest (добавить поле photo)

```python
# visitors/forms.py

class GuestRegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=255, label="ФИО гостя")
    email = forms.EmailField(required=False, label="Email")
    phone_number = forms.CharField(max_length=20, required=False, label="Телефон")
    iin = forms.CharField(max_length=12, required=False, label="ИИН")
    
    # NEW: Добавить поле для фото
    photo = forms.ImageField(required=False, label="Фото гостя")
    
    # ... остальные поля
```

## Итоговая инструкция

### ✅ ДЛЯ РАБОТЫ С ФОТО ПРЯМО СЕЙЧАС:

1. **Используйте ТОЛЬКО flow групповых приглашений**
2. Создайте приглашение в админке
3. Отправьте ссылку гостю
4. Гость заполняет форму С ФОТО
5. Finalize - фото автоматически загрузится в HikCentral

### ✅ ДЛЯ ДОБАВЛЕНИЯ ФОТО В ПРЯМУЮ РЕГИСТРАЦИЮ:

1. Добавьте поле `photo` в модель `Guest`
2. Создайте и примените миграцию
3. Добавьте поле `photo` в форму регистрации
4. Обновите view чтобы сохранять фото в `guest.photo`
5. Логика в `enroll_face_task` уже готова читать из `Guest.photo`

---
**Дата**: 2025-10-03  
**Статус**: ⚠️ ЧАСТИЧНО РАБОТАЕТ (только через GuestInvitation)  
**Требуется**: Добавить поле photo в Guest для полной функциональности
