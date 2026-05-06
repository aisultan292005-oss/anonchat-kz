"""Admin broadcast — send message to all users."""
import asyncio
import logging
from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from sqlalchemy import select

import database.repo as repo
from database.models import User
from database.engine import async_session_factory
from config import ADMIN_IDS
from utils.design import DIV

logger = logging.getLogger(__name__)
router = Router()


class BroadcastStates(StatesGroup):
    waiting_message = State()
    confirm = State()


def broadcast_kb() -> object:
    b = InlineKeyboardBuilder()
    b.button(text="📢 Всем пользователям", callback_data="broadcast:all")
    b.button(text="⭐ Только Premium", callback_data="broadcast:premium")
    b.button(text="🏙 По городу", callback_data="broadcast:city")
    b.row(InlineKeyboardButton(text="← Назад", callback_data="admin:back"))
    b.adjust(1)
    return b.as_markup()


def confirm_kb() -> object:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast:send"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast:cancel"),
    )
    return b.as_markup()


def city_select_kb() -> object:
    from database.cities import KZ_CITIES
    b = InlineKeyboardBuilder()
    for label, city in KZ_CITIES[:10]:
        b.button(text=city, callback_data=f"broadcast_city:{city}")
    b.row(InlineKeyboardButton(text="← Назад", callback_data="admin:back"))
    b.adjust(2)
    return b.as_markup()


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(
        f"<b>Рассылка</b>\n{DIV}\n"
        f"Выберите аудиторию:",
        reply_markup=broadcast_kb(),
    )


@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    await call.message.edit_text(
        f"<b>Рассылка</b>\n{DIV}\n"
        f"Выберите аудиторию:",
        reply_markup=broadcast_kb(),
    )


@router.callback_query(F.data == "broadcast:all")
async def cb_broadcast_all(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return
    await state.update_data(target="all", city=None)
    await state.set_state(BroadcastStates.waiting_message)
    await call.message.edit_text(
        f"<b>Рассылка всем</b>\n{DIV}\n"
        f"Напишите текст сообщения.\n"
        f"Поддерживается <b>HTML</b> форматирование.\n\n"
        f"Пример: <code>Привет! &lt;b&gt;Новая функция&lt;/b&gt; уже доступна!</code>"
    )


@router.callback_query(F.data == "broadcast:premium")
async def cb_broadcast_premium(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return
    await state.update_data(target="premium", city=None)
    await state.set_state(BroadcastStates.waiting_message)
    await call.message.edit_text(
        f"<b>Рассылка Premium пользователям</b>\n{DIV}\n"
        f"Напишите текст сообщения:"
    )


@router.callback_query(F.data == "broadcast:city")
async def cb_broadcast_city(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    await call.message.edit_text(
        f"<b>Рассылка по городу</b>\n{DIV}\n"
        f"Выберите город:",
        reply_markup=city_select_kb(),
    )


@router.callback_query(F.data.startswith("broadcast_city:"))
async def cb_broadcast_city_select(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return
    city = call.data.split(":")[1]
    await state.update_data(target="city", city=city)
    await state.set_state(BroadcastStates.waiting_message)
    await call.message.edit_text(
        f"<b>Рассылка · {city}</b>\n{DIV}\n"
        f"Напишите текст сообщения:"
    )


@router.message(BroadcastStates.waiting_message)
async def process_broadcast_msg(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.update_data(text=message.text or message.caption or "")
    await state.update_data(
        photo=message.photo[-1].file_id if message.photo else None,
        caption=message.caption,
    )

    data = await state.get_data()
    target_label = {
        "all": "всем пользователям",
        "premium": "Premium пользователям",
        "city": f"жителям {data.get('city', '')}",
    }.get(data.get("target"), "всем")

    # Count recipients
    count = await _count_recipients(data.get("target"), data.get("city"))

    await state.set_state(BroadcastStates.confirm)
    preview = (message.text or message.caption or "")[:200]
    await message.answer(
        f"<b>Подтверждение рассылки</b>\n{DIV}\n"
        f"Кому: <b>{target_label}</b>\n"
        f"Получателей: <b>{count}</b>\n\n"
        f"Текст:\n{preview}\n\n"
        f"Отправить?",
        reply_markup=confirm_kb(),
    )


@router.callback_query(F.data == "broadcast:send", BroadcastStates.confirm)
async def cb_broadcast_send(call: CallbackQuery, state: FSMContext, bot: Bot):
    if call.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    await state.clear()

    await call.message.edit_text(f"<b>Рассылка запущена...</b>\n{DIV}\nПодождите.")

    sent, failed = await _do_broadcast(
        bot=bot,
        target=data.get("target", "all"),
        city=data.get("city"),
        text=data.get("text", ""),
        photo=data.get("photo"),
        caption=data.get("caption"),
        admin_id=call.from_user.id,
    )

    await call.message.edit_text(
        f"<b>Рассылка завершена</b>\n{DIV}\n"
        f"✅ Доставлено: <b>{sent}</b>\n"
        f"❌ Не доставлено: <b>{failed}</b>"
    )
    logger.info("Broadcast by admin %s: sent=%s failed=%s", call.from_user.id, sent, failed)


@router.callback_query(F.data == "broadcast:cancel")
async def cb_broadcast_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        f"<b>Рассылка отменена</b>\n{DIV}",
        reply_markup=broadcast_kb(),
    )


@router.callback_query(F.data == "admin:back")
async def cb_admin_back(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    from keyboards import admin_kb
    stats = await repo.get_stats()
    await call.message.edit_text(
        f"🛠 <b>Админ-панель</b>\n{DIV}\n"
        f"👥 Пользователей: <b>{stats['total_users']}</b>\n"
        f"💬 Активных чатов: <b>{stats['active_chats']}</b>\n"
        f"📋 Жалоб: <b>{stats['open_reports']}</b>",
        reply_markup=admin_kb(),
    )


async def _count_recipients(target: str, city: str | None) -> int:
    async with async_session_factory() as s:
        if target == "all":
            q = select(User).where(User.is_registered == True, User.is_banned == False)
        elif target == "premium":
            q = select(User).where(User.is_premium == True, User.is_banned == False)
        elif target == "city" and city:
            q = select(User).where(User.city == city, User.is_registered == True, User.is_banned == False)
        else:
            q = select(User).where(User.is_registered == True)
        result = await s.execute(q)
        return len(result.scalars().all())


async def _do_broadcast(
    bot: Bot, target: str, city: str | None,
    text: str, photo: str | None, caption: str | None,
    admin_id: int,
) -> tuple[int, int]:
    async with async_session_factory() as s:
        if target == "all":
            q = select(User.id).where(User.is_registered == True, User.is_banned == False)
        elif target == "premium":
            q = select(User.id).where(User.is_premium == True, User.is_banned == False)
        elif target == "city" and city:
            q = select(User.id).where(User.city == city, User.is_registered == True, User.is_banned == False)
        else:
            q = select(User.id).where(User.is_registered == True)
        result = await s.execute(q)
        user_ids = [row[0] for row in result.fetchall()]

    # Add bot branding
    broadcast_text = f"📢 <b>Сообщение от администратора</b>\n{DIV}\n{text}"

    sent = 0
    failed = 0
    for uid in user_ids:
        if uid == admin_id:
            continue
        try:
            if photo:
                await bot.send_photo(uid, photo, caption=f"📢 <b>Сообщение от администратора</b>\n{DIV}\n{caption or ''}")
            else:
                await bot.send_message(uid, broadcast_text)
            sent += 1
        except Exception:
            failed += 1
        # Rate limit: 30 messages/second max
        if sent % 25 == 0:
            await asyncio.sleep(1)

    return sent, failed
