"""Beautiful welcome screen with image + commands menu."""
import logging
from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

import database.repo as repo
from utils.design import DIV

logger = logging.getLogger(__name__)
router = Router()

# ── Welcome image ────────────────────────────────────────────────────────────
# Path to local image file — uploaded once, then Telegram caches the file_id
import os
WELCOME_IMAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "welcome.jpg")
WELCOME_IMAGE_FILE_ID = None  # cached after first send

WELCOME_TEXT = (
    "👋 <b>Привет! Добро пожаловать в AnonChat KZ</b>\n\n"
    "🇰🇿 Анонимный чат для казахстанцев!\n"
    "Общайся с незнакомцами — никто не узнает кто ты.\n\n"
    "🔒 Чат строго <b>18+</b>\n"
    "💬 Общение 1 на 1 с случайными собеседниками\n"
    "📍 Люди со всего Казахстана\n\n"
    "Нажми кнопку ниже чтобы начать!"
)

HELP_TEXT = (
    f"<b>Команды бота</b>\n{DIV}\n"
    "🔍 /search — Найти собеседника\n"
    "⏭ /next — Следующий собеседник\n"
    "🛑 /stop — Завершить диалог\n"
    "⭐ /premium — Premium подписка\n"
    "🚪 /rooms — Тематические комнаты\n"
    "🔧 /filters — Фильтры поиска\n"
    "📊 /stats — Статистика\n"
    "👥 /ref — Реферальная программа\n"
    "🔔 /notify — Уведомления\n"
    f"{DIV}\n"
    "❓ По вопросам: @admin"
)


# ── Bottom menu keyboard (always visible) ─────────────────────────────────────

def bottom_menu_kb() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="🚀 Начать диалог"))
    b.row(
        KeyboardButton(text="🔍 Поиск по полу"),
        KeyboardButton(text="📚 Интересы поиска"),
    )
    return b.as_markup(resize_keyboard=True)


def chat_bottom_kb() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="⏭ Следующий"))
    b.row(
        KeyboardButton(text="📞 Позвонить"),
        KeyboardButton(text="🎁 Подарок"),
    )
    b.row(
        KeyboardButton(text="🚨 Пожаловаться"),
        KeyboardButton(text="🛑 Завершить диалог"),
    )
    return b.as_markup(resize_keyboard=True)


def queue_bottom_kb() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="❌ Отмена поиска"))
    return b.as_markup(resize_keyboard=True)


# ── Start inline buttons ──────────────────────────────────────────────────────

def start_inline_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🚀 Начать диалог", callback_data="quick:search"))
    b.row(
        InlineKeyboardButton(text="🔍 Поиск по полу", callback_data="quick:gender"),
        InlineKeyboardButton(text="🚪 Комнаты", callback_data="quick:rooms"),
    )
    b.row(
        InlineKeyboardButton(text="⭐ Premium", callback_data="quick:premium"),
        InlineKeyboardButton(text="📖 Помощь", callback_data="quick:help"),
    )
    return b.as_markup()


def gender_search_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="👨 Искать парней", callback_data="qs_gender:male"),
        InlineKeyboardButton(text="👩 Искать девушек", callback_data="qs_gender:female"),
    )
    b.row(InlineKeyboardButton(text="🎲 Случайно", callback_data="qs_gender:any"))
    b.row(InlineKeyboardButton(text="← Назад", callback_data="quick:back"))
    return b.as_markup()


# ── Handlers ──────────────────────────────────────────────────────────────────

async def _send_welcome(message, text: str, reply_markup=None):
    """Send welcome photo with caption, fallback to text."""
    global WELCOME_IMAGE_FILE_ID
    from aiogram.types import FSInputFile

    # Try cached file_id first
    if WELCOME_IMAGE_FILE_ID:
        try:
            await message.answer_photo(
                photo=WELCOME_IMAGE_FILE_ID,
                caption=text,
                reply_markup=reply_markup,
            )
            return
        except Exception:
            WELCOME_IMAGE_FILE_ID = None

    # Try local file
    if os.path.exists(WELCOME_IMAGE_PATH):
        try:
            sent = await message.answer_photo(
                photo=FSInputFile(WELCOME_IMAGE_PATH),
                caption=text,
                reply_markup=reply_markup,
            )
            # Cache file_id for future use
            if sent.photo:
                WELCOME_IMAGE_FILE_ID = sent.photo[-1].file_id
            return
        except Exception:
            pass

    # Fallback to text only
    await message.answer(text, reply_markup=reply_markup)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await repo.get_or_create_user(message.from_user.id, message.from_user.username)

    # Handle referral
    args = message.text.split() if message.text else []
    if len(args) > 1 and args[1].startswith("ref_") and not user.is_registered:
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            await state.update_data(referrer_id=referrer_id)
        except ValueError:
            pass

    if user.is_registered:
        # Returning user
        from database.cities import KZ_CITIES
        city_label = next((c for l, c in KZ_CITIES if c == user.city), user.city or "Казахстан")
        text = (
            f"👋 <b>С возвращением!</b>\n{DIV}\n"
            f"📍 {city_label}\n"
            f"💬 Чатов проведено: <b>{user.total_chats}</b>\n"
            f"⭐ Рейтинг: <b>{user.reputation}</b>\n\n"
            f"Нажми <b>🚀 Начать диалог</b>!"
        )
        await _send_welcome(message, text, start_inline_kb())
        await message.answer(
            "Выберите действие:",
            reply_markup=bottom_menu_kb(),
        )
        return

    # New user — show welcome + start registration
    if not user.captcha_passed:
        await _send_welcome(message, WELCOME_TEXT)
        from handlers.captcha import send_captcha
        await send_captcha(message, state)
        return

    # Captcha passed but not registered
    from handlers.registration import RegStates
    from keyboards import gender_kb
    await state.set_state(RegStates.waiting_gender)
    await message.answer(
        f"<b>Регистрация  ●○○○</b>\n{DIV}\nУкажите ваш пол:",
        reply_markup=gender_kb(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT)


@router.message(Command("search"))
async def cmd_search(message: Message, bot: Bot):
    user = await repo.get_user(message.from_user.id)
    if not user or not user.is_registered:
        await message.answer("Сначала пройдите регистрацию: /start")
        return
    from handlers.chat import _do_search
    await _do_search(message.from_user.id, user, bot)


@router.message(Command("next"))
async def cmd_next(message: Message, bot: Bot):
    from handlers.chat import _end_chat, _do_search
    if repo.in_chat(message.from_user.id):
        await _end_chat(message.from_user.id, bot, reason="next")
        user = await repo.get_user(message.from_user.id)
        await _do_search(message.from_user.id, user, bot)
    else:
        await message.answer("Вы не в чате.")


@router.message(Command("stop"))
async def cmd_stop(message: Message, bot: Bot):
    from handlers.chat import _end_chat
    from utils.design import msg_chat_ended
    if repo.in_chat(message.from_user.id):
        await _end_chat(message.from_user.id, bot)
        await message.answer(msg_chat_ended(), reply_markup=bottom_menu_kb())
    elif repo.in_queue(message.from_user.id):
        repo.dequeue(message.from_user.id)
        await message.answer("Поиск отменён.", reply_markup=bottom_menu_kb())
    else:
        await message.answer("Вы не в чате.")


@router.message(Command("premium"))
async def cmd_premium(message: Message):
    from handlers.premium import btn_premium
    await btn_premium(message)


@router.message(Command("rooms"))
async def cmd_rooms(message: Message):
    from handlers.rooms import btn_rooms
    await btn_rooms(message)


@router.message(Command("filters"))
async def cmd_filters(message: Message):
    from handlers.filters_setup import btn_filters
    await btn_filters(message)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    from handlers.stats_user import btn_stats
    await btn_stats(message)


@router.message(Command("ref"))
async def cmd_ref(message: Message, bot: Bot):
    from handlers.referral import btn_referral
    await btn_referral(message, bot)


@router.message(Command("notify"))
async def cmd_notify(message: Message):
    from handlers.notifications import btn_notifications
    await btn_notifications(message)


# ── Bottom menu buttons ───────────────────────────────────────────────────────

@router.message(F.text == "🚀 Начать диалог")
async def btn_start_dialog(message: Message, bot: Bot):
    user = await repo.get_user(message.from_user.id)
    if not user or not user.is_registered:
        await message.answer("Сначала пройдите регистрацию: /start")
        return
    if repo.in_chat(message.from_user.id):
        await message.answer("Вы уже в чате.")
        return
    from handlers.chat import _do_search
    await _do_search(message.from_user.id, user, bot)


@router.message(F.text == "🔍 Поиск по полу")
async def btn_gender_search(message: Message):
    is_prem = await repo.is_premium_active(message.from_user.id)
    if not is_prem:
        from config import PREMIUM_PRICE_XTR
        await message.answer(
            f"<b>Поиск по полу</b>\n{DIV}\n"
            f"Эта функция доступна только для <b>Premium</b> пользователей.\n\n"
            f"Стоимость: <b>{PREMIUM_PRICE_XTR} ⭐ Stars</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⭐ Купить Premium", callback_data="buy_premium")
            ]])
        )
        return
    await message.answer(
        f"<b>Поиск по полу</b>\n{DIV}\nКого ищем?",
        reply_markup=gender_search_kb(),
    )


@router.message(F.text == "📚 Интересы поиска")
async def btn_interests_search(message: Message):
    from handlers.filters_setup import btn_filters
    await btn_filters(message)


@router.message(F.text == "🛑 Завершить диалог")
async def btn_stop_dialog(message: Message, bot: Bot):
    from handlers.chat import _end_chat
    from utils.design import msg_chat_ended
    if repo.in_chat(message.from_user.id):
        await _end_chat(message.from_user.id, bot)
        await message.answer(msg_chat_ended(), reply_markup=bottom_menu_kb())
    elif repo.in_queue(message.from_user.id):
        repo.dequeue(message.from_user.id)
        await message.answer("Поиск отменён.", reply_markup=bottom_menu_kb())
    else:
        await message.answer("Вы не в чате.", reply_markup=bottom_menu_kb())


# ── Inline quick actions ──────────────────────────────────────────────────────

@router.callback_query(F.data == "quick:search")
async def cb_quick_search(call: CallbackQuery, bot: Bot):
    user = await repo.get_user(call.from_user.id)
    if not user or not user.is_registered:
        await call.answer("Сначала пройдите регистрацию: /start", show_alert=True)
        return
    await call.answer()
    from handlers.chat import _do_search
    await _do_search(call.from_user.id, user, bot)


@router.callback_query(F.data == "quick:gender")
async def cb_quick_gender(call: CallbackQuery):
    is_prem = await repo.is_premium_active(call.from_user.id)
    if not is_prem:
        await call.answer("Только для Premium пользователей!", show_alert=True)
        return
    await call.message.edit_reply_markup(reply_markup=gender_search_kb())


@router.callback_query(F.data.startswith("qs_gender:"))
async def cb_qs_gender(call: CallbackQuery, bot: Bot):
    val = call.data.split(":")[1]
    from database.models import Gender
    if val == "any":
        await repo.update_user(call.from_user.id, pref_gender=None)
    elif val == "male":
        await repo.update_user(call.from_user.id, pref_gender=Gender.male)
    else:
        await repo.update_user(call.from_user.id, pref_gender=Gender.female)
    await call.answer("✅ Фильтр установлен!")
    user = await repo.get_user(call.from_user.id)
    from handlers.chat import _do_search
    await _do_search(call.from_user.id, user, bot)


@router.callback_query(F.data == "quick:rooms")
async def cb_quick_rooms(call: CallbackQuery):
    await call.answer()
    from handlers.rooms import btn_rooms
    await btn_rooms(call.message)


@router.callback_query(F.data == "quick:premium")
async def cb_quick_premium(call: CallbackQuery):
    await call.answer()
    from handlers.premium import btn_premium
    await btn_premium(call.message)


@router.callback_query(F.data == "quick:help")
async def cb_quick_help(call: CallbackQuery):
    await call.message.edit_text(HELP_TEXT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="← Назад", callback_data="quick:back")
    ]]))


@router.callback_query(F.data == "quick:back")
async def cb_quick_back(call: CallbackQuery):
    try:
        await call.message.edit_caption(caption=WELCOME_TEXT, reply_markup=start_inline_kb())
    except Exception:
        await call.message.edit_text(WELCOME_TEXT, reply_markup=start_inline_kb())
