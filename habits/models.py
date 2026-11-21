"""Модели приложения habits."""

from django.conf import settings
from django.db import models

from habits.validators import validate_duration, validate_periodicity


class Habit(models.Model):
    """Привычка: я буду [действие] в [время] в [место]."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habits",
        verbose_name="Создатель",
    )
    place = models.CharField(max_length=255, verbose_name="Место")
    time = models.TimeField(verbose_name="Время", help_text="Время, когда нужно выполнять привычку.")
    action = models.CharField(max_length=255, verbose_name="Действие")
    is_pleasant = models.BooleanField(
        default=False,
        verbose_name="Приятная привычка",
        help_text="Приятную привычку можно привязать к полезной в качестве вознаграждения.",
    )
    related_habit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_habits",
        verbose_name="Связанная привычка",
        help_text="Приятная привычка, которую можно выполнить после полезной.",
    )
    periodicity = models.PositiveSmallIntegerField(
        default=1,
        validators=[validate_periodicity],
        verbose_name="Периодичность, дней",
        help_text="Как часто выполнять привычку: от 1 до 7 дней.",
    )
    reward = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Вознаграждение",
        help_text="Чем вознаградить себя после выполнения.",
    )
    duration = models.PositiveSmallIntegerField(
        validators=[validate_duration],
        verbose_name="Время на выполнение, секунд",
        help_text="Не больше 120 секунд.",
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name="Публичная",
        help_text="Публичные привычки видят все пользователи.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")

    class Meta:
        """Мета-параметры модели Habit."""

        verbose_name = "Привычка"
        verbose_name_plural = "Привычки"
        ordering = ("id",)

    def __str__(self) -> str:
        """Возвращает привычку в формате из книги."""
        return f"Я буду {self.action} в {self.time:%H:%M} в {self.place}"
