# 🕵️ AnonChat Bot — Анонимный Telegram Чат

Полнофункциональный анонимный чат-бот для Telegram с Premium-подпиской, модерацией и админ-панелью.

---

## 📁 Структура проекта

```
premium_anon_bot/
├── bot.py                  # Точка входа
├── config.py               # Все настройки из .env
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
│
├── database/
│   ├── __init__.py
│   ├── engine.py           # SQLAlchemy engine + init_db()
│   ├── models.py           # ORM модели (User, Session, Report, Payment)
│   └── repo.py             # Все операции с БД + in-memory очередь
│
├── handlers/
│   ├── __init__.py         # Сборка всех роутеров
│   ├── registration.py     # /start, FSM регистрации (пол, возраст)
│   ├── chat.py             # Поиск, матчмейкинг, ретрансляция сообщений
│   ├── reports.py          # Кнопка "Пожаловаться"
│   ├── premium.py          # Оплата, активация Premium, фильтры
│   ├── admin.py            # Жалобы, бан, статистика для админов
│   └── settings.py         # Профиль пользователя, статистика
│
├── keyboards/
│   └── __init__.py         # Все клавиатуры (Reply + Inline)
│
├── middlewares/
│   └── __init__.py         # AntiSpam, BanCheck, InactivityWatcher
│
└── utils/
    └── logging_setup.py    # Ротируемые логи
```

---

## ⚙️ Установка и запуск

### Вариант 1: Docker (рекомендуется)

```bash
# 1. Клонируй/скопируй проект
cd premium_anon_bot

# 2. Настрой .env
cp .env.example .env
nano .env   # вставь BOT_TOKEN и ADMIN_IDS

# 3. Запусти
docker-compose up -d

# 4. Логи
docker-compose logs -f bot
```

### Вариант 2: Локально

**Требования:** Python 3.11+, PostgreSQL 14+

```bash
# 1. Создай виртуальное окружение
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 2. Установи зависимости
pip install -r requirements.txt

# 3. Создай БД PostgreSQL
createdb anonbot

# 4. Настрой .env
cp .env.example .env
# Заполни BOT_TOKEN, ADMIN_IDS, DATABASE_URL

# 5. Запусти
python bot.py
```

---

## 🔑 Как получить токен бота

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Напиши `/newbot`
3. Придумай имя и username для бота
4. Скопируй токен в `.env` → `BOT_TOKEN=...`
5. Отправь `/setprivacy` → выбери бота → `Disable` (чтобы получать все сообщения в группах)

---

## 💳 Настройка оплаты (Telegram Stars)

Telegram Stars (`XTR`) встроены в Telegram и не требуют `PAYMENT_PROVIDER_TOKEN` — оставь его пустым.

Для реальных денег (через ЮKassa, Stripe и т.д.):
1. Открой [@BotFather](https://t.me/BotFather)
2. `/mybots` → твой бот → `Payments`
3. Выбери провайдера, получи токен
4. Вставь в `PAYMENT_PROVIDER_TOKEN=`
5. Измени `currency` в `handlers/premium.py` на `RUB` / `USD`

---

## 🎮 Команды бота

| Команда / Кнопка | Кто | Описание |
|---|---|---|
| `/start` | Все | Регистрация / главное меню |
| `🔍 Найти собеседника` | Все | Начать поиск партнёра |
| `⏭ Следующий` | В чате | Сменить собеседника |
| `🚪 Завершить` | В чате | Выйти из чата |
| `🚨 Пожаловаться` | В чате | Отправить жалобу модератору |
| `⭐ Premium` | Все | Купить подписку / настроить фильтр |
| `📊 Статистика` | Все | Общая статистика |
| `⚙️ Настройки` | Все | Свой профиль |
| `/admin` | Админ | Панель управления |
| `/ban <id>` | Админ | Заблокировать пользователя |
| `/unban <id>` | Админ | Разблокировать пользователя |

---

## 🛡️ Система безопасности

| Функция | Описание |
|---|---|
| **Возраст 18+** | Блокировка при вводе возраста < 18 |
| **Анти-спам** | Макс. 5 сообщений за 5 секунд |
| **Таймер неактивности** | Авто-разрыв через 5 минут тишины |
| **Бан-лист** | Проверка при каждом сообщении |
| **История для жалоб** | Последние 10 сообщений хранятся в БД |
| **Ротируемые логи** | Файл `bot.log`, макс. 5MB × 3 бэкапа |

---

## ⭐ Premium-возможности

- 🎯 **Выбор пола собеседника** — только парни / только девушки / случайно
- ⚡ **Приоритетный поиск** — Premium-пользователи находят партнёра быстрее
- Подписка на **30 дней** за **100 ⭐ Stars**

---

## 🗄️ База данных

Таблицы PostgreSQL:

| Таблица | Назначение |
|---|---|
| `users` | Профили, пол, возраст, premium, бан |
| `sessions` | История чат-сессий |
| `chat_messages` | Последние 10 сообщений для модерации |
| `reports` | Жалобы пользователей |
| `payments` | История оплат |

---

## 🚀 Деплой на VPS (Ubuntu)

```bash
# systemd-сервис
sudo nano /etc/systemd/system/anonbot.service
```

```ini
[Unit]
Description=AnonChat Telegram Bot
After=network.target postgresql.service

[Service]
WorkingDirectory=/home/ubuntu/premium_anon_bot
ExecStart=/home/ubuntu/premium_anon_bot/venv/bin/python bot.py
Restart=always
RestartSec=5
User=ubuntu
EnvironmentFile=/home/ubuntu/premium_anon_bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable anonbot
sudo systemctl start anonbot
sudo journalctl -u anonbot -f   # логи
```
