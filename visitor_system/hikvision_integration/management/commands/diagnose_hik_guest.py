from django.core.management.base import BaseCommand, CommandError
from typing import Optional
from hikvision_integration.models import HikAccessTask, HikPersonBinding, HikDevice
from visitors.models import Visit


class Command(BaseCommand):
    help = "Диагностика интеграции Hikvision по visit_id или guest_id"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--visit", type=int, dest="visit_id", help="ID визита")
        parser.add_argument("--guest", type=int, dest="guest_id", help="ID гостя")

    def handle(self, *args, **options) -> None:
        visit_id: Optional[int] = options.get("visit_id")
        guest_id: Optional[int] = options.get("guest_id")

        if not visit_id and not guest_id:
            raise CommandError("Укажите хотя бы один из параметров: --visit или --guest")

        visit: Optional[Visit] = None
        if visit_id:
            visit = Visit.objects.filter(id=visit_id).first()
            if not visit:
                raise CommandError(f"Visit {visit_id} не найден")
            guest_id = guest_id or getattr(getattr(visit, "guest", None), "id", None)

        self.stdout.write(self.style.NOTICE("=== БАЗОВАЯ ИНФОРМАЦИЯ ==="))
        if visit:
            self.stdout.write(f"Visit ID: {visit.id}, status={visit.status}")
        self.stdout.write(f"Guest ID: {guest_id}")

        # Задачи
        self.stdout.write(self.style.NOTICE("\n=== ЗАДАЧИ HikAccessTask ==="))
        tasks_qs = HikAccessTask.objects.all()
        if visit:
            tasks_qs = tasks_qs.filter(visit_id=visit.id)
        if guest_id:
            tasks_qs = tasks_qs.filter(guest_id=guest_id)
        tasks = list(tasks_qs.order_by("-created_at").values("id", "kind", "status", "attempts", "last_error", "created_at"))
        if not tasks:
            self.stdout.write("Задач не найдено")
        else:
            for t in tasks:
                self.stdout.write(f"Task #{t['id']}: kind={t['kind']} status={t['status']} attempts={t['attempts']}")
                if t.get("last_error"):
                    self.stdout.write(self.style.WARNING(f"  last_error: {t['last_error']}"))

        # Биндинги
        self.stdout.write(self.style.NOTICE("\n=== BINDINGS HikPersonBinding ==="))
        bindings_qs = HikPersonBinding.objects.all()
        if guest_id:
            bindings_qs = bindings_qs.filter(guest_id=guest_id)
        bindings = list(bindings_qs.select_related("device").values("id", "guest_id", "person_id", "face_id", "status", "access_from", "access_to", "device__name"))
        if not bindings:
            self.stdout.write("Биндингов не найдено")
        else:
            for b in bindings:
                self.stdout.write(
                    f"Binding #{b['id']}: guest={b['guest_id']} person={b['person_id']} face={b['face_id']} status={b['status']} device={b['device__name']}"
                )

        # Устройства
        self.stdout.write(self.style.NOTICE("\n=== УСТРОЙСТВА ==="))
        devices = list(HikDevice.objects.filter(enabled=True).values("id", "name", "host", "port", "is_primary", "doors_json"))
        if not devices:
            self.stdout.write("Нет активных устройств")
        else:
            for d in devices:
                self.stdout.write(
                    f"Device #{d['id']}: {d['name']} {d['host']}:{d['port']} primary={d['is_primary']} doors={d['doors_json']}"
                )

        self.stdout.write(self.style.SUCCESS("\nДиагностика завершена"))


