# 🚀 QUICK START: HikCentral Integration

## 1. Запуск системы

```powershell
# Terminal 1: Celery Worker
cd d:\university_visitor_system
start_celery.bat

# Terminal 2: Django
cd d:\university_visitor_system\visitor_system
poetry run python manage.py runserver
```

## 2. Создание гостя С ФОТО

```
1. Откройте: http://127.0.0.1:8000/visits/group-invitation/
2. Создайте приглашение
3. Скопируйте ссылку приглашения
4. Откройте ссылку (как гость)
5. Заполните форму + загрузите фото
6. Submit → Finalize
7. Проверьте HikCentral UI
```

## 3. Проверка статуса

```powershell
# Статусы задач
cd d:\university_visitor_system\visitor_system
poetry run python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev'); import django; django.setup(); from hikvision_integration.models import HikAccessTask; tasks = HikAccessTask.objects.order_by('-id')[:5]; print('\n'.join([f'{t.id}: {t.kind} - {t.status}' for t in tasks]))"

# Логи worker
Get-Content celery_hikvision_error.log -Tail 20
```

## 4. Troubleshooting

### Задачи в queued
```powershell
# Перезапустить worker
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "celery.*worker" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
cd d:\university_visitor_system
start_celery.bat
```

### Нет фото
- Используйте ТОЛЬКО групповые приглашения
- Прямая регистрация `/visits/register-guest/` БЕЗ фото!

## 5. Важные файлы

- `start_celery.bat` - запуск worker
- `CELERY_HIKVISION_FIX.md` - решение проблемы Celery
- `PHOTO_UPLOAD_SOLUTION.md` - решение проблемы с фото
- `FINAL_INTEGRATION_REPORT.md` - полный отчёт

---
✅ **Worker запущен** = Celery worker ready  
✅ **Задача выполнена** = status: success  
✅ **Гость в HCP** = Visit.hikcentral_person_id заполнен
