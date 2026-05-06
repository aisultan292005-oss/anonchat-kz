"""
Anonymous video/audio calls via Jitsi Meet.
Bot generates a unique room link and sends it to both users.
No server needed — Jitsi is free and public.
"""
import logging
import random
import string
import asyncio
from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database.repo as repo
from utils.design import DIV

logger = logging.getLogger(__name__)
router = Router()

# Pending call requests: {caller_id: {"partner_id": int, "room": str}}
_pending_calls: dict[int, dict] = {}


def _gen_room() -> str:
    """Generate unique anonymous room ID."""
    chars = string.ascii_letters + string.digits
    rand = "".join(random.choices(chars, k=10))
    return f"AnonChatKZ_{rand}"


def call_request_kb(caller_id: int, room: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Принять", callback_data=f"call_accept:{caller_id}:{room}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"call_reject:{caller_id}"),
    )
    return b.as_markup()


def call_type_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="📞 Аудиозвонок", callback_data="call_type:audio"),
        InlineKeyboardButton(text="📹 Видеозвонок", callback_data="call_type:video"),
    )
    b.row(InlineKeyboardButton(text="← Отмена", callback_data="call_type:cancel"))
    return b.as_markup()


def join_call_kb(room: str, call_type: str) -> InlineKeyboardMarkup:
    # Jitsi supports #config.startWithVideoMuted=true for audio-only
    config = "" if call_type == "video" else "#config.startWithVideoMuted=true"
    url = f"https://meet.jit.si/{room}{config}"
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔗 Открыть звонок", url=url))
    return b.as_markup()


# ── /call command ─────────────────────────────────────────────────────────────

@router.message(Command("call"))
@router.message(F.text == "📞 Позвонить")
async def cmd_call(message: Message):
    user_id = message.from_user.id

    if not repo.in_chat(user_id):
        await message.answer(
            f"<b>Звонок</b>\n{DIV}\n"
            f"Звонки доступны только во время активного чата.\n"
            f"Сначала найдите собеседника."
        )
        return

    partner_id = repo.get_partner(user_id)
    if not partner_id:
        return

    await message.answer(
        f"<b>Анонимный звонок</b>\n{DIV}\n"
        f"Выберите тип звонка:",
        reply_markup=call_type_kb(),
    )


@router.callback_query(F.data.startswith("call_type:"))
async def cb_call_type(call: CallbackQuery, bot: Bot):
    val = call.data.split(":")[1]
    user_id = call.from_user.id

    if val == "cancel":
        await call.message.edit_text("Звонок отменён.")
        return

    if not repo.in_chat(user_id):
        await call.answer("Вы не в чате!", show_alert=True)
        return

    partner_id = repo.get_partner(user_id)
    if not partner_id:
        await call.answer("Собеседник недоступен!", show_alert=True)
        return

    room = _gen_room()
    _pending_calls[user_id] = {"partner_id": partner_id, "room": room, "type": val}

    call_label = "📹 Видеозвонок" if val == "video" else "📞 Аудиозвонок"

    await call.message.edit_text(
        f"<b>{call_label} отправлен</b>\n{DIV}\n"
        f"Ожидаем ответа собеседника...\n"
        f"Запрос действует <b>30 секунд</b>"
    )

    # Notify partner
    await bot.send_message(
        partner_id,
        f"<b>Входящий {call_label.lower()}</b>\n{DIV}\n"
        f"Собеседник предлагает анонимный звонок.\n"
        f"Ваши личные данные не раскрываются.",
        reply_markup=call_request_kb(user_id, room),
    )

    # Auto-cancel after 30 seconds
    asyncio.create_task(_auto_cancel_call(user_id, partner_id, bot))
    logger.info("Call request: %s -> %s (%s)", user_id, partner_id, val)


async def _auto_cancel_call(caller_id: int, partner_id: int, bot: Bot):
    await asyncio.sleep(30)
    if caller_id in _pending_calls:
        _pending_calls.pop(caller_id, None)
        try:
            await bot.send_message(
                caller_id,
                f"<b>Звонок не принят</b>\n{DIV}\n"
                f"Собеседник не ответил в течение 30 секунд."
            )
        except Exception:
            pass


# ── Accept / Reject ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("call_accept:"))
async def cb_call_accept(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    caller_id = int(parts[1])
    room = parts[2]

    pending = _pending_calls.pop(caller_id, None)
    if not pending:
        await call.message.edit_text(
            f"<b>Звонок недоступен</b>\n{DIV}\nЗапрос истёк или был отменён."
        )
        return

    call_type = pending.get("type", "video")
    call_label = "📹 Видеозвонок" if call_type == "video" else "📞 Аудиозвонок"
    config = "" if call_type == "video" else "#config.startWithVideoMuted=true"
    url = f"https://meet.jit.si/{room}{config}"

    join_text = (
        f"<b>{call_label} · Подключение</b>\n{DIV}\n"
        f"Нажмите кнопку ниже для входа в звонок.\n\n"
        f"🔒 Комната анонимная — никто не знает кто вы\n"
        f"🌐 Откроется в браузере вашего телефона\n"
        f"🎙 Разрешите доступ к микрофону/камере"
    )

    # Send join link to both
    await call.message.edit_text(join_text, reply_markup=join_call_kb(room, call_type))
    await bot.send_message(caller_id, join_text, reply_markup=join_call_kb(room, call_type))

    logger.info("Call accepted: %s <-> %s room=%s", caller_id, call.from_user.id, room)


@router.callback_query(F.data.startswith("call_reject:"))
async def cb_call_reject(call: CallbackQuery, bot: Bot):
    caller_id = int(call.data.split(":")[1])
    _pending_calls.pop(caller_id, None)

    await call.message.edit_text(
        f"<b>Звонок отклонён</b>\n{DIV}\nВы отклонили входящий звонок."
    )
    try:
        await bot.send_message(
            caller_id,
            f"<b>Звонок отклонён</b>\n{DIV}\nСобеседник не принял звонок."
        )
    except Exception:
        pass

    logger.info("Call rejected: %s -> %s", caller_id, call.from_user.id)
