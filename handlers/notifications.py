"""Push notifications — notify users when someone is searching."""
import asyncio
import logging
from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

import database.repo as repo
from utils.design import DIV

logger = logging.getLogger(__name__)
router = Router()

# Users who want notifications: {user_id: True}
_notify_users: set[int] = set()
_notified_recently: set[int] = set()  # prevent spam


def notif_settings_kb(enabled: bool) -> object:
    b = InlineKeyboardBuilder()
    if enabled:
        b.button(text="🔕 Выключить уведомления", callback_data="notif:off")
    else:
        b.button(text="🔔 Включить уведомления", callback_data="notif:on")
    b.row(InlineKeyboardButton(text="← Назад", callback_data="nav:main"))
    b.adjust(1)
    return b.as_markup()


@router.message(F.text == "🔔 Уведомления")
async def btn_notifications(message: Message):
    enabled = message.from_user.id in _notify_users
    status = "включены ✅" if enabled else "выключены ❌"
    await message.answer(
        f"<b>Уведомления</b>\n{DIV}\n"
        f"Статус: <b>{status}</b>\n\n"
        f"Когда включены — бот уведомит вас,\n"
        f"если кто-то ищет собеседника прямо сейчас.",
        reply_markup=notif_settings_kb(enabled),
    )


@router.callback_query(F.data == "notif:on")
async def cb_notif_on(call: CallbackQuery):
    _notify_users.add(call.from_user.id)
    await call.message.edit_text(
        f"<b>Уведомления включены</b>\n{DIV}\n"
        f"Вы получите сообщение, когда кто-то начнёт поиск.",
        reply_markup=notif_settings_kb(True),
    )


@router.callback_query(F.data == "notif:off")
async def cb_notif_off(call: CallbackQuery):
    _notify_users.discard(call.from_user.id)
    await call.message.edit_text(
        f"<b>Уведомления выключены</b>\n{DIV}\n"
        f"Вы не будете получать уведомления о поиске.",
        reply_markup=notif_settings_kb(False),
    )


async def notify_searchers(new_user_id: int, bot: Bot):
    """Called when a user starts searching — notify subscribed users."""
    to_notify = [
        uid for uid in _notify_users
        if uid != new_user_id
        and uid not in _notified_recently
        and not repo.in_chat(uid)
        and not repo.in_queue(uid)
    ]

    for uid in to_notify[:5]:  # max 5 at once
        try:
            _notified_recently.add(uid)
            await bot.send_message(
                uid,
                f"<b>Кто-то ищет собеседника!</b>\n{DIV}\n"
                f"Прямо сейчас кто-то ждёт вас в чате.\n"
                f"Нажмите <b>🔍 Найти собеседника</b>!"
            )
            # Remove from recently notified after 5 min
            asyncio.create_task(_clear_notified(uid))
        except Exception as e:
            logger.warning("Failed to notify %s: %s", uid, e)


async def _clear_notified(user_id: int):
    await asyncio.sleep(300)
    _notified_recently.discard(user_id)
