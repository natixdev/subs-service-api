import asyncio
import json
from collections.abc import AsyncGenerator

from app.core.config import settings

_clients: list[asyncio.Queue[dict[str, str]]] = []


async def broadcast(event: str, data: dict) -> None:
    """Отправляет SSE-событие всем подключенным клиентам."""
    payload = json.dumps(data, default=str)

    for queue in list(_clients):
        await queue.put(
            {
                'event': event,
                'data': payload,
            },
        )


async def event_generator() -> AsyncGenerator[dict[str, str], None]:
    """Генератор событий для SSE."""
    queue: asyncio.Queue[dict[str, str]] = asyncio.Queue()
    _clients.append(queue)

    try:~
        while True:
            try:
                event = await asyncio.wait_for(
                    queue.get(),
                    timeout=settings.sse_keepalive_interval,
                )
                yield event

            except asyncio.TimeoutError:
                yield {'comment': 'ping'}
    finally:
        _clients.remove(queue)
