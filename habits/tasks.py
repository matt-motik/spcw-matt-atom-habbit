"""Отложенные задачи приложения habits."""

from celery import shared_task
from django.utils import timezone

from habits.services import build_reminder, get_habits_to_remind, send_telegram_message


@shared_task
def send_habit_reminders() -> int:
    """Отправляет в Telegram напоминания о привычках, время которых наступило. Возвращает число отправленных."""
    now = timezone.localtime()
    sent = 0
    for habit in get_habits_to_remind(now):
        if send_telegram_message(habit.owner.tg_chat_id, build_reminder(habit)):
            habit.last_reminder = now.date()
            habit.save(update_fields=["last_reminder"])
            sent += 1
    return sent
