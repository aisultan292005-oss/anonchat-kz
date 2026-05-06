from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, LabeledPrice,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config import PREMIUM_PRICE_XTR
from database.models import INTERESTS_LIST, ROOM_LIST


# ── Reply keyboards ───────────────────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="🔍 Найти собеседника"))
    b.row(KeyboardButton(text="🔄 Продолжить с последним"))
    b.row(KeyboardButton(text="🚪 Комнаты"), KeyboardButton(text="🎁 Подарок"))
    b.row(KeyboardButton(text="🔧 Фильтры"), KeyboardButton(text="⭐ Premium"))
    b.row(KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚙️ Настройки"))
    b.row(KeyboardButton(text="👥 Рефералы"), KeyboardButton(text="🔔 Уведомления"))
    return b.as_markup(resize_keyboard=True)


def chat_kb() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="⏭ Следующий"))
    b.row(KeyboardButton(text="🎁 Подарок"), KeyboardButton(text="🚨 Пожаловаться"))
    b.row(KeyboardButton(text="🚪 Завершить"))
    return b.as_markup(resize_keyboard=True)


def queue_kb() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="❌ Отмена поиска"))
    return b.as_markup(resize_keyboard=True)


def continue_chat_kb() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="🔍 Найти собеседника"))
    b.row(KeyboardButton(text="🔄 Продолжить с последним"))
    return b.as_markup(resize_keyboard=True)


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ── Back button helper ────────────────────────────────────────────────────────

def back_btn(callback: str = "nav:main") -> InlineKeyboardButton:
    return InlineKeyboardButton(text="← Назад", callback_data=callback)


# ── Inline keyboards ──────────────────────────────────────────────────────────

def gender_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="👨 Мужской", callback_data="reg_gender:male"),
        InlineKeyboardButton(text="👩 Женский", callback_data="reg_gender:female"),
    )
    return b.as_markup()


def confirm_age_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Подтверждаю (18+)", callback_data="age_confirm"),
        InlineKeyboardButton(text="← Назад", callback_data="reg_back:gender"),
    )
    return b.as_markup()


INTEREST_EMOJI = {
    "музыка": "🎵", "спорт": "⚽", "игры": "🎮", "кино": "🎬",
    "аниме": "🎌", "технологии": "💻", "путешествия": "✈️",
    "книги": "📚", "искусство": "🎨", "кулинария": "🍳",
}


def interests_kb(selected: list, prefix: str = "interest") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for interest in INTERESTS_LIST:
        emoji = INTEREST_EMOJI.get(interest, "•")
        tick = "✅ " if interest in selected else ""
        b.button(text=f"{tick}{emoji} {interest}", callback_data=f"{prefix}:{interest}")
    b.row(
        InlineKeyboardButton(text="← Назад", callback_data=f"{prefix}_back"),
        InlineKeyboardButton(text=f"Готово ({len(selected)})", callback_data=f"{prefix}:done"),
    )
    b.adjust(2)
    return b.as_markup()


def city_kb(prefix: str = "reg_city") -> InlineKeyboardMarkup:
    from database.cities import KZ_CITIES
    b = InlineKeyboardBuilder()
    for label, city in KZ_CITIES:
        b.button(text=city, callback_data=f"{prefix}:{city}")
    b.row(InlineKeyboardButton(text="← Назад", callback_data=f"{prefix}_back"))
    b.adjust(2)
    return b.as_markup()


def premium_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text=f"⭐ Купить Premium ({PREMIUM_PRICE_XTR} Stars)",
        callback_data="buy_premium",
    ))
    b.row(InlineKeyboardButton(text="← Назад", callback_data="nav:main"))
    return b.as_markup()


def pref_gender_kb(current_pref: str | None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(
            text=f"{'✅ ' if current_pref == 'male' else ''}👨 Парни",
            callback_data="pref:male",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if current_pref == 'female' else ''}👩 Девушки",
            callback_data="pref:female",
        ),
    )
    b.row(InlineKeyboardButton(
        text=f"{'✅ ' if current_pref is None else ''}🎲 Случайно",
        callback_data="pref:none",
    ))
    b.row(InlineKeyboardButton(text="← Назад", callback_data="nav:main"))
    return b.as_markup()


def report_reason_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    reasons = [
        ("🔞 Непристойный контент", "report:indecent"),
        ("🤬 Оскорбления", "report:insults"),
        ("🤖 Спам / бот", "report:spam"),
        ("⚠️ Другое", "report:other"),
    ]
    for text, cb in reasons:
        b.row(InlineKeyboardButton(text=text, callback_data=cb))
    b.row(InlineKeyboardButton(text="← Назад", callback_data="report:cancel"))
    return b.as_markup()


def filter_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🎂 Возраст", callback_data="filter:age")
    b.button(text="🎯 Интересы", callback_data="filter:interests")
    b.button(text="🚪 Комната", callback_data="filter:room")
    b.button(text="🌐 Язык", callback_data="filter:lang")
    b.button(text="🔄 Сбросить", callback_data="filter:reset")
    b.row(InlineKeyboardButton(text="← Назад", callback_data="nav:main"))
    b.adjust(2)
    return b.as_markup()


def age_range_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    ranges = [
        ("18–22", "18-22"), ("23–27", "23-27"), ("28–35", "28-35"),
        ("36–45", "36-45"), ("46+", "46-99"), ("🎲 Любой", "any"),
    ]
    for label, val in ranges:
        b.button(text=label, callback_data=f"age_range:{val}")
    b.row(InlineKeyboardButton(text="← Назад", callback_data="filter:back"))
    b.adjust(3)
    return b.as_markup()


def room_kb(current: str | None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for room in ROOM_LIST:
        prefix = "✅ " if room == current else ""
        b.button(text=f"{prefix}{room.capitalize()}", callback_data=f"room:{room}")
    b.button(text=f"{'✅ ' if current is None else ''}🎲 Любая", callback_data="room:any")
    b.row(InlineKeyboardButton(text="← Назад", callback_data="filter:back"))
    b.adjust(2)
    return b.as_markup()


def lang_kb(current: str) -> InlineKeyboardMarkup:
    langs = [("🇷🇺 Русский", "ru"), ("🇬🇧 English", "en"), ("🇰🇿 Қазақша", "kz")]
    b = InlineKeyboardBuilder()
    for label, code in langs:
        prefix = "✅ " if code == current else ""
        b.button(text=f"{prefix}{label}", callback_data=f"lang:{code}")
    b.row(InlineKeyboardButton(text="← Назад", callback_data="filter:back"))
    b.adjust(1)
    return b.as_markup()


def admin_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast"))
    b.row(InlineKeyboardButton(text="📋 Жалобы", callback_data="admin:reports"))
    b.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"))
    return b.as_markup()


def admin_report_kb(report_id: int, reported_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🔨 Забанить", callback_data=f"admin_ban:{reported_id}:{report_id}"),
        InlineKeyboardButton(text="✅ Закрыть", callback_data=f"admin_close:{report_id}"),
    )
    return b.as_markup()


def settings_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📍 Изменить город", callback_data="settings:city")
    b.button(text="🎯 Изменить интересы", callback_data="settings:interests")
    b.row(InlineKeyboardButton(text="← Назад", callback_data="nav:main"))
    b.adjust(1)
    return b.as_markup()
