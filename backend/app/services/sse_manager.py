"""SSE 连接管理器 — Redis Pub/Sub 桥接 Celery Worker ↔ FastAPI"""

import asyncio
import json
import threading
from contextlib import suppress
from uuid import UUID

import redis

from app.core.config import settings


class SSEManager:
    def __init__(self):
        self._connections: dict[UUID, set[asyncio.Queue]] = {}
        self._redis = redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        self._listener_thread = threading.Thread(target=self._listen_redis, daemon=True)
        self._started = False

    def start(self):
        if self._started:
            return
        self._started = True
        self._listener_thread.start()

    async def subscribe(self, task_id: UUID) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        if task_id not in self._connections:
            self._connections[task_id] = set()
            self._pubsub.subscribe(f"task:{task_id}")
        self._connections[task_id].add(queue)
        await queue.put(f"data: {json.dumps({'event': 'connected', 'task_id': str(task_id)})}\n\n")
        return queue

    def unsubscribe(self, task_id: UUID, queue: asyncio.Queue):
        if task_id not in self._connections:
            return
        self._connections[task_id].discard(queue)
        if not self._connections[task_id]:
            del self._connections[task_id]
            self._pubsub.unsubscribe(f"task:{task_id}")

    def publish(self, task_id: UUID, event: str, data: dict):
        payload = json.dumps({"event": event, "data": data})
        self._redis.publish(f"task:{task_id}", payload)

    def _listen_redis(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with suppress(Exception):
            for message in self._pubsub.listen():
                if message["type"] != "message":
                    continue
                task_id_str = message["channel"].replace("task:", "")
                try:
                    task_uuid = UUID(task_id_str)
                except ValueError:
                    continue
                try:
                    payload = json.loads(message["data"])
                    event = payload.get("event", "message")
                    data = payload.get("data", {})
                except json.JSONDecodeError:
                    continue
                sse_message = f"event: {event}\ndata: {json.dumps(data)}\n\n"
                if task_uuid in self._connections:
                    for queue in self._connections[task_uuid].copy():
                        with suppress(Exception):
                            loop.call_soon_threadsafe(queue.put_nowait, sse_message)


sse_manager = SSEManager()
