import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

import database.repo as repo
from config import ANTI_SPAM_MESSAGES, ANTI_SPAM_WINDOW, INACTIVITY_TIMEOUT

logger = logging.getLogger(__name__)

# ── Anti-spam ─────────────────────────────────────────────────────────────────

class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self):
        self._buckets: dict[int, deque] = defaultdict(deque)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.monotonic()
        bucket = self._buckets[user_id]

        # Remove old timestamps
        while bucket and now - bucket[0] > ANTI_SPAM_WINDOW:
            bucket.popleft()

        if len(bucket) >= ANTI_SPAM_MESSAGES:
            await event.answer("⏳ Слишком много сообщений. Подожди несколько секунд.")
            logger.warning("Spam detected from user %s", user_id)
            return  # Drop the update

        bucket.append(now)
        return await handler(event, data)


# ── Inactivity watcher ────────────────────────────────────────────────────────

_inactivity_tasks: dict[int, asyncio.Task] = {}


def reset_inactivity_timer(user_id: int, bot) -> None:
    """Call whenever a user sends a message in an active chat."""
    task = _inactivity_tasks.get(user_id)
    if task:
        task.cancel()
    _inactivity_tasks[user_id] = asyncio.create_task(
        _inactivity_watchdog(user_id, bot)
    )


def cancel_inactivity_timer(user_id: int) -> None:
    task = _inactivity_tasks.pop(user_id, None)
    if task:
        task.cancel()


async def _inactivity_watchdog(user_id: int, bot) -> None:
    try:
        await asyncio.sleep(INACTIVITY_TIMEOUT)
        if repo.in_chat(user_id):
            partner_id = repo.get_partner(user_id)
            session_id = repo.get_session_db_id(user_id)
            repo.disconnect(user_id)
            if session_id:
                await repo.close_session(session_id)
            cancel_inactivity_timer(partner_id)
            from utils.design import msg_inactivity, msg_inactivity_partner
            await bot.send_message(user_id, msg_inactivity())
            if partner_id:
                await bot.send_message(partner_id, msg_inactivity_partner())
            logger.info("Inactivity disconnect: %s <-> %s", user_id, partner_id)
    except asyncio.CancelledError:
        pass


# ── Ban check middleware ───────────────────────────────────────────────────────

class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)
        user = await repo.get_user(event.from_user.id)
        if user and user.is_banned:
            await event.answer("🚫 Ты заблокирован в этом боте.")
            return
        return await handler(event, data)
