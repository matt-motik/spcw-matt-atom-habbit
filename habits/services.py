"""Сервисные функции приложения habits: выбор привычек для напоминания и отправка в Telegram."""

import logging
from datetime import datetime

import requests
from django.conf import settings
from django.db.models import Q, QuerySet

from habits.models import Habit

logger = logging.getLogger(__name__)

TELEGRAM_TIMEOUT = 10


def send_telegram_message(chat_id: str, text: str) -> bool:
    """Отправляет сообщение через Telegram Bot API. Возвращает True, если Telegram его принял."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN не задан, сообщение в чат %s не отправлено", chat_id)
        return False
    url = f"{settings.TELEGRAM_API_URL}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=TELEGRAM_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as error:
        # Токен входит в URL, поэтому в лог пишется только тип ошибки и статус
        status = getattr(error.response, "status_code", None)
        logger.error("Не удалось отправить сообщение в чат %s: %s, статус %s", chat_id, type(error).__name__, status)
        return False
    return True


def is_reminder_due(habit: Habit, now: datetime) -> bool:
    """Возвращает True, если с прошлого напоминания прошло не меньше дней, чем периодичность привычки."""
    if habit.last_reminder is None:
        return True
    return bool((now.date() - habit.last_reminder).days >= habit.periodicity)


def get_habits_to_remind(now: datetime) -> list[Habit]:
    """Полезные привычки, время которых уже наступило сегодня и по которым пора напомнить.

    Время привычки сравнивается с текущим временем в часовом поясе проекта. Если задача
    пропустила нужную минуту, напоминание придёт при следующем запуске в тот же день.
    """
    habits: QuerySet[Habit] = (
        Habit.objects.filter(is_pleasant=False, time__lte=now.time())
        .filter(Q(last_reminder__isnull=True) | Q(last_reminder__lt=now.date()))
        .exclude(owner__tg_chat_id="")
        .select_related("owner", "related_habit")
    )
    return [habit for habit in habits if is_reminder_due(habit, now)]


def build_reminder(habit: Habit) -> str:
    """Текст напоминания: что, когда и где сделать и чем себя вознаградить."""
    lines = [
        f"Напоминание: я буду {habit.action} в {habit.time:%H:%M} {habit.place}.",
        f"На выполнение — {habit.duration} сек.",
    ]
    if habit.related_habit:
        lines.append(f"После этого можно: {habit.related_habit.action}.")
    elif habit.reward:
        lines.append(f"Награда: {habit.reward}.")
    return "\n".join(lines)
