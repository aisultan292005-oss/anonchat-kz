"""
Professional message design system — Telegram Premium style.
All bot messages go through these templates.
"""

# ── Dividers ──────────────────────────────────────────────────────────────────
DIV = "――――――――――――――――――"
DIV_SM = "─────────────"

# ── System messages ───────────────────────────────────────────────────────────

def msg_welcome_back(city: str, total_chats: int) -> str:
    return (
        f"<b>Добро пожаловать</b>\n"
        f"{DIV}\n"
        f"📍 Город: <b>{city}</b>\n"
        f"💬 Чатов: <b>{total_chats}</b>\n"
        f"{DIV}\n"
        f"Нажмите <b>Найти собеседника</b> для начала"
    )


def msg_welcome_new() -> str:
    return (
        f"<b>Анонимный чат · Казахстан</b>\n"
        f"{DIV}\n"
        f"Общайтесь анонимно с людьми со всего Казахстана.\n"
        f"Ваша личность полностью защищена.\n"
        f"{DIV}\n"
        f"Пройдите короткую регистрацию для начала"
    )


def msg_partner_found(gender: str, age: int, city: str, interests_common: int, room: str | None) -> str:
    gender_label = "Мужчина" if gender == "male" else "Женщина"
    lines = [
        f"<b>Собеседник найден</b>",
        DIV,
        f"• {gender_label}, {age} лет",
        f"• {city}" if city else None,
        f"• Комната: {room.capitalize()}" if room else None,
        f"• Общих интересов: {interests_common}" if interests_common > 0 else None,
        DIV,
        "Общение начато. Ваши данные скрыты.",
    ]
    return "\n".join(l for l in lines if l is not None)


def msg_searching() -> str:
    return (
        f"<b>Поиск собеседника...</b>\n"
        f"{DIV}\n"
        f"Подбираем подходящего собеседника.\n"
        f"Чат начнётся автоматически."
    )


def msg_partner_left() -> str:
    return (
        f"<b>Собеседник покинул чат</b>\n"
        f"{DIV}\n"
        f"Нажмите <b>Найти собеседника</b> для нового диалога\n"
        f"или <b>Продолжить с последним</b> для повтора"
    )


def msg_partner_switched() -> str:
    return (
        f"<b>Собеседник переключился</b>\n"
        f"{DIV}\n"
        f"Подбираем нового собеседника..."
    )


def msg_chat_ended() -> str:
    return (
        f"<b>Чат завершён</b>\n"
        f"{DIV}\n"
        f"Нажмите <b>Найти собеседника</b> для нового диалога"
    )


def msg_inactivity() -> str:
    return (
        f"<b>Чат завершён</b>\n"
        f"{DIV}\n"
        f"Соединение разорвано из-за неактивности"
    )


def msg_inactivity_partner() -> str:
    return (
        f"<b>Чат завершён</b>\n"
        f"{DIV}\n"
        f"Собеседник был неактивен"
    )


def msg_not_in_chat() -> str:
    return "Вы не в чате. Нажмите <b>Найти собеседника</b>."


def msg_already_in_chat() -> str:
    return "Вы уже в чате. Используйте <b>Следующий</b> или <b>Завершить</b>."


def msg_search_cancelled() -> str:
    return (
        f"<b>Поиск отменён</b>\n"
        f"{DIV_SM}\n"
        f"Нажмите <b>Найти собеседника</b> для повтора"
    )


def msg_continue_last(gender: str, age: int, city: str) -> str:
    gender_label = "Мужчина" if gender == "male" else "Женщина"
    return (
        f"<b>Повтор чата</b>\n"
        f"{DIV}\n"
        f"• {gender_label}, {age} лет\n"
        f"• {city}\n"
        f"{DIV}\n"
        f"Соединение восстановлено"
    )


def msg_continue_incoming() -> str:
    return (
        f"<b>Повторное соединение</b>\n"
        f"{DIV}\n"
        f"Предыдущий собеседник хочет продолжить диалог"
    )


# ── Registration ──────────────────────────────────────────────────────────────

def msg_reg_step(step: int, total: int, text: str) -> str:
    progress = "●" * step + "○" * (total - step)
    return f"<b>Регистрация  {progress}</b>\n{DIV}\n{text}"


def msg_reg_complete(city: str, interests: str) -> str:
    return (
        f"<b>Регистрация завершена</b>\n"
        f"{DIV}\n"
        f"📍 Город: <b>{city}</b>\n"
        f"🎯 Интересы: <b>{interests or 'не выбраны'}</b>\n"
        f"{DIV}\n"
        f"Нажмите <b>Найти собеседника</b> для начала"
    )


# ── Premium ───────────────────────────────────────────────────────────────────

def msg_premium_info(until: str, pref: str) -> str:
    return (
        f"<b>Premium · Активен</b>\n"
        f"{DIV}\n"
        f"Действует до: <b>{until}</b>\n"
        f"Фильтр: <b>{pref}</b>\n"
        f"{DIV}\n"
        f"Привилегии:\n"
        f"  · Выбор пола собеседника\n"
        f"  · Приоритетный поиск"
    )


def msg_premium_offer(price: int, days: int) -> str:
    return (
        f"<b>Premium подписка</b>\n"
        f"{DIV}\n"
        f"Стоимость: <b>{price} ⭐ Stars · {days} дней</b>\n"
        f"{DIV}\n"
        f"Возможности:\n"
        f"  · Выбор пола собеседника\n"
        f"  · Приоритетный поиск"
    )


def msg_premium_activated(days: int, until: str) -> str:
    return (
        f"<b>Premium активирован</b>\n"
        f"{DIV}\n"
        f"Срок: <b>{days} дней</b>\n"
        f"До: <b>{until}</b>\n"
        f"{DIV}\n"
        f"Выберите фильтр в разделе ⭐ Premium"
    )


# ── Stats ─────────────────────────────────────────────────────────────────────

def msg_user_stats(user, avg_len, peak_str, days, global_stats) -> str:
    return (
        f"<b>Статистика</b>\n"
        f"{DIV}\n"
        f"Чатов проведено: <b>{user.total_chats}</b>\n"
        f"Сообщений отправлено: <b>{user.total_messages}</b>\n"
        f"Средняя длина диалога: <b>{avg_len}</b>\n"
        f"Пик активности: <b>{peak_str}</b>\n"
        f"В сервисе: <b>{days} дней</b>\n"
        f"{DIV}\n"
        f"Онлайн сейчас: <b>{global_stats['active_chats'] * 2 + global_stats['in_queue']}</b> пользователей"
    )


def msg_global_stats(s) -> str:
    return (
        f"<b>Статистика сервиса</b>\n"
        f"{DIV}\n"
        f"Пользователей: <b>{s['total_users']}</b>\n"
        f"Активных чатов: <b>{s['active_chats']}</b>\n"
        f"В поиске: <b>{s['in_queue']}</b>\n"
        f"Всего сессий: <b>{s['total_sessions']}</b>"
    )


# ── Reports ───────────────────────────────────────────────────────────────────

def msg_report_sent() -> str:
    return (
        f"<b>Жалоба отправлена</b>\n"
        f"{DIV}\n"
        f"Модератор рассмотрит обращение.\n"
        f"Спасибо за помощь в обеспечении безопасности."
    )


# ── Profile ───────────────────────────────────────────────────────────────────

def msg_profile(user, is_prem: bool, city_label: str) -> str:
    g = "Мужской" if str(user.gender) in ("Gender.male","male") else "Женский"
    prem = "Активен" if is_prem else "Не активен"
    interests = user.interests or "не выбраны"
    rep = getattr(user, "reputation", 0)
    refs = getattr(user, "referral_count", 0)
    return (
        f"<b>Профиль</b>\n"
        f"{DIV}\n"
        f"ID: <code>{user.id}</code>\n"
        f"Пол: <b>{g}</b>\n"
        f"Возраст: <b>{user.age}</b>\n"
        f"Город: <b>{city_label}</b>\n"
        f"Интересы: <b>{interests}</b>\n"
        f"Premium: <b>{prem}</b>\n"
        f"Рейтинг: <b>{rep} ⭐</b>\n"
        f"Рефералов: <b>{refs}</b>\n"
        f"{DIV}\n"
        f"Чатов: <b>{user.total_chats}</b>  ·  Сообщений: <b>{user.total_messages}</b>"
    )
