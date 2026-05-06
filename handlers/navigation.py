"""Global navigation handler — back buttons."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import (
    main_menu_kb, filter_menu_kb, settings_kb,
    premium_kb, pref_gender_kb,
)
from utils.design import DIV
import database.repo as repo

router = Router()


@router.callback_query(F.data == "nav:main")
async def cb_nav_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.message.answer(
        f"<b>Главное меню</b>\n{DIV}\nВыберите действие:",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "filter:back")
async def cb_filter_back(call: CallbackQuery):
    user = await repo.get_user(call.from_user.id)
    age_label = f"{user.pref_age_min}–{user.pref_age_max}" if user and user.pref_age_min else "Любой"
    interests = (user.interests or "не выбраны") if user else "не выбраны"
    room = (user.preferred_room or "любая") if user else "любая"
    lang = (user.language or "ru") if user else "ru"
    await call.message.edit_text(
        f"<b>Фильтры поиска</b>\n{DIV}\n"
        f"🎂 Возраст: <b>{age_label}</b>\n"
        f"🎯 Интересы: <b>{interests}</b>\n"
        f"🚪 Комната: <b>{room}</b>\n"
        f"🌐 Язык: <b>{lang}</b>",
        reply_markup=filter_menu_kb(),
    )


@router.callback_query(F.data.startswith("reg_back:"))
async def cb_reg_back(call: CallbackQuery, state: FSMContext):
    step = call.data.split(":")[1]
    from handlers.registration import RegStates
    from keyboards import gender_kb
    if step == "gender":
        await state.set_state(RegStates.waiting_gender)
        await call.message.edit_text(
            "Укажите ваш пол:",
            reply_markup=gender_kb(),
        )


@router.message(F.text == "🔙 Главное меню")
async def btn_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"<b>Главное меню</b>\n{DIV}\nВыберите действие:",
        reply_markup=main_menu_kb(),
    )
