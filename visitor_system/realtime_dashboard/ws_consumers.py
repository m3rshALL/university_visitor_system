import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .services import dashboard_service


class DashboardConsumer(AsyncWebsocketConsumer):
    group_name = "dashboard_updates"

    async def connect(self):
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # Отправляем начальные метрики (не блокируем event loop)
        metrics = await sync_to_async(dashboard_service.get_current_metrics)()
        await self.send_json({
            "type": "initial",
            "data": metrics,
        })

    async def disconnect(self):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None):
        try:
            message = json.loads(text_data or "{}")
        except Exception:
            message = {}
        # Пока: поддерживаем ping
        if message.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content, ensure_ascii=False))

    # Handler для групповых сообщений
    async def dashboard_broadcast(self, event):
        await self.send_json(event.get("message", {}))


