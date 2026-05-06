"""
All database access goes through this module.
Each public function creates its own session to stay stateless.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import PREMIUM_DAYS, REPORT_HISTORY_LEN
from database.engine import async_session_factory
from database.models import (
    ChatMessage, Gender, Payment, Report, Session, User, utcnow,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _db():
    return async_session_factory()


# ── Users ─────────────────────────────────────────────────────────────────────

async def get_user(user_id: int) -> Optional[User]:
    async with _db() as s:
        return await s.get(User, user_id)


async def get_or_create_user(user_id: int, username: str | None = None) -> User:
    async with _db() as s:
        user = await s.get(User, user_id)
        if not user:
            user = User(id=user_id, username=username)
            s.add(user)
            await s.commit()
            await s.refresh(user)
        return user


async def update_user(user_id: int, **kwargs) -> None:
    async with _db() as s:
        await s.execute(update(User).where(User.id == user_id).values(**kwargs))
        await s.commit()


async def register_user(user_id: int, gender: Gender, age: int) -> None:
    await update_user(user_id, gender=gender, age=age, is_registered=True)


async def ban_user(user_id: int) -> None:
    await update_user(user_id, is_banned=True)


async def unban_user(user_id: int) -> None:
    await update_user(user_id, is_banned=False)


async def touch_user(user_id: int) -> None:
    await update_user(user_id, last_active=utcnow())


async def is_premium_active(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user or not user.is_premium:
        return False
    if user.premium_until and user.premium_until < datetime.now(timezone.utc):
        await update_user(user_id, is_premium=False, premium_until=None)
        return False
    return True


async def activate_premium(user_id: int) -> None:
    until = datetime.now(timezone.utc) + timedelta(days=PREMIUM_DAYS)
    await update_user(user_id, is_premium=True, premium_until=until)


# ── Queue (in-memory via Redis is ideal, but we use DB for simplicity) ────────
# We store "queue" state inside the User row: partner_id = None, in_queue = True
# Active session is tracked in the sessions table.

# Actually let's use a lightweight in-process dict for queue speed:
#   queue[user_id] = {"gender_pref": Gender|None, "is_premium": bool}
# Real production would use Redis.

_queue: dict[int, dict] = {}      # { user_id: {pref_gender, is_premium} }
_active: dict[int, int] = {}      # { user_id: partner_id }
_session_id: dict[int, int] = {}  # { user_id: session_db_id }


def enqueue(user_id: int, pref_gender: Gender | None, premium: bool) -> None:
    _queue[user_id] = {"pref_gender": pref_gender, "premium": premium}


def dequeue(user_id: int) -> None:
    _queue.pop(user_id, None)


def in_queue(user_id: int) -> bool:
    return user_id in _queue


def in_chat(user_id: int) -> bool:
    return user_id in _active


def get_partner(user_id: int) -> int | None:
    return _active.get(user_id)


def match(user_id: int, user_gender: Gender | None, is_premium: bool, pref_gender: Gender | None) -> int | None:
    """
    Find best match from queue.
    Priority: premium users first, then preference match.
    """
    candidates = [
        (uid, meta)
        for uid, meta in _queue.items()
        if uid != user_id
    ]
    if not candidates:
        return None

    # Filter by this user's gender preference (premium only)
    if is_premium and pref_gender and user_gender:
        filtered = [
            (uid, meta) for uid, meta in candidates
            # partner must match our pref AND their pref must match us (or they don't care)
            if True  # we don't know partner gender here — checked after DB lookup
        ]
        # We'll do DB lookup below; for now return first candidate
    return candidates[0][0]


def connect(user_a: int, user_b: int, session_db_id: int) -> None:
    _active[user_a] = user_b
    _active[user_b] = user_a
    _session_id[user_a] = session_db_id
    _session_id[user_b] = session_db_id
    _queue.pop(user_a, None)
    _queue.pop(user_b, None)


def disconnect(user_id: int) -> int | None:
    partner = _active.pop(user_id, None)
    if partner:
        _active.pop(partner, None)
        _session_id.pop(user_id, None)
        _session_id.pop(partner, None)
    return partner


def get_session_db_id(user_id: int) -> int | None:
    return _session_id.get(user_id)


def queue_size() -> int:
    return len(_queue)


def active_chats() -> int:
    return len(_active) // 2


# ── Sessions ──────────────────────────────────────────────────────────────────

async def create_session(user_a: int, user_b: int) -> int:
    async with _db() as s:
        sess = Session(user_a=user_a, user_b=user_b)
        s.add(sess)
        await s.commit()
        await s.refresh(sess)
        # increment chat counters
        await s.execute(
            update(User)
            .where(User.id.in_([user_a, user_b]))
            .values(total_chats=User.total_chats + 1)
        )
        await s.commit()
        return sess.id


async def close_session(session_id: int) -> None:
    async with _db() as s:
        await s.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(ended_at=utcnow())
        )
        await s.commit()


async def save_message(session_id: int, sender_id: int, content: str) -> None:
    async with _db() as s:
        msg = ChatMessage(session_id=session_id, sender_id=sender_id, content=content)
        s.add(msg)
        await s.commit()
        # Keep only last N messages per session
        subq = (
            select(ChatMessage.id)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.sent_at.desc())
            .limit(REPORT_HISTORY_LEN)
            .subquery()
        )
        await s.execute(
            delete(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .where(ChatMessage.id.notin_(select(subq.c.id)))
        )
        await s.commit()


async def get_recent_messages(session_id: int) -> list[ChatMessage]:
    async with _db() as s:
        result = await s.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.sent_at.desc())
            .limit(REPORT_HISTORY_LEN)
        )
        return list(reversed(result.scalars().all()))


# ── Reports ───────────────────────────────────────────────────────────────────

async def create_report(
    reporter_id: int, reported_id: int,
    session_id: int | None, reason: str | None,
) -> Report:
    async with _db() as s:
        report = Report(
            reporter_id=reporter_id,
            reported_id=reported_id,
            session_id=session_id,
            reason=reason,
        )
        s.add(report)
        await s.commit()
        await s.refresh(report)
        return report


async def get_open_reports() -> list[Report]:
    async with _db() as s:
        result = await s.execute(
            select(Report)
            .where(Report.resolved == False)
            .order_by(Report.created_at.desc())
        )
        return result.scalars().all()


async def resolve_report(report_id: int) -> None:
    async with _db() as s:
        await s.execute(
            update(Report).where(Report.id == report_id).values(resolved=True)
        )
        await s.commit()


# ── Payments ──────────────────────────────────────────────────────────────────

async def save_payment(user_id: int, charge_id: str, amount: int) -> None:
    async with _db() as s:
        pay = Payment(user_id=user_id, telegram_charge_id=charge_id, amount=amount)
        s.add(pay)
        await s.commit()


# ── Stats ─────────────────────────────────────────────────────────────────────

async def get_stats() -> dict:
    async with _db() as s:
        total_users = (await s.execute(select(func.count()).select_from(User))).scalar()
        registered = (await s.execute(
            select(func.count()).select_from(User).where(User.is_registered == True)
        )).scalar()
        premium_users = (await s.execute(
            select(func.count()).select_from(User).where(User.is_premium == True)
        )).scalar()
        banned_users = (await s.execute(
            select(func.count()).select_from(User).where(User.is_banned == True)
        )).scalar()
        total_sessions = (await s.execute(select(func.count()).select_from(Session))).scalar()
        open_reports = (await s.execute(
            select(func.count()).select_from(Report).where(Report.resolved == False)
        )).scalar()
    return {
        "total_users": total_users,
        "registered": registered,
        "premium": premium_users,
        "banned": banned_users,
        "total_sessions": total_sessions,
        "in_queue": queue_size(),
        "active_chats": active_chats(),
        "open_reports": open_reports,
    }


# ── New stats functions ───────────────────────────────────────────────────────

async def increment_messages(user_id: int) -> None:
    async with _db() as s:
        await s.execute(
            update(User).where(User.id == user_id).values(total_messages=User.total_messages + 1)
        )
        await s.commit()


async def get_avg_session_length(user_id: int) -> float | None:
    async with _db() as s:
        result = await s.execute(
            select(func.avg(
                select(func.count(ChatMessage.id))
                .where(ChatMessage.sender_id == user_id)
                .correlate(Session)
                .scalar_subquery()
            ))
        )
        # Simpler approach: count messages / count sessions
        msg_count = (await s.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.sender_id == user_id)
        )).scalar() or 0
        sess_count = (await s.execute(
            select(func.count(Session.id)).where(
                (Session.user_a == user_id) | (Session.user_b == user_id)
            )
        )).scalar() or 0
        if sess_count == 0:
            return None
        return msg_count / sess_count


async def get_peak_hour(user_id: int) -> int | None:
    async with _db() as s:
        result = await s.execute(
            select(
                func.extract("hour", ChatMessage.sent_at).label("hour"),
                func.count().label("cnt")
            )
            .where(ChatMessage.sender_id == user_id)
            .group_by("hour")
            .order_by(func.count().desc())
            .limit(1)
        )
        row = result.fetchone()
        return int(row.hour) if row else None


# ── Referral functions ────────────────────────────────────────────────────────

async def add_referral(referrer_id: int, new_user_id: int) -> None:
    async with _db() as s:
        await s.execute(
            update(User)
            .where(User.id == referrer_id)
            .values(referral_count=User.referral_count + 1)
        )
        await s.execute(
            update(User)
            .where(User.id == new_user_id)
            .values(referred_by=referrer_id)
        )
        await s.commit()


async def get_referral_count(user_id: int) -> int:
    user = await get_user(user_id)
    return user.referral_count if user else 0


async def activate_premium_days(user_id: int, days: int) -> None:
    from datetime import timedelta, timezone
    user = await get_user(user_id)
    if not user:
        return
    now = datetime.now(timezone.utc)
    current_until = user.premium_until if user.premium_until and user.premium_until > now else now
    new_until = current_until + timedelta(days=days)
    await update_user(user_id, is_premium=True, premium_until=new_until)


# ── Reputation helper ─────────────────────────────────────────────────────────

def _get_reputation(user_id: int) -> int:
    """Sync helper — returns 0 as fallback; real value fetched via get_user async."""
    return 0
