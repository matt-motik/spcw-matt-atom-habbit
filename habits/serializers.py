"""Сериализаторы приложения habits."""

from rest_framework import serializers

from habits.models import Habit
from habits.validators import PleasantHabitValidator, RelatedHabitValidator, RewardOrRelatedHabitValidator


class HabitSerializer(serializers.ModelSerializer):
    """Сериализатор привычки. Создатель подставляется автоматически."""

    class Meta:
        """Мета-параметры сериализатора привычки."""

        model = Habit
        fields = (
            "id",
            "owner",
            "action",
            "time",
            "place",
            "is_pleasant",
            "related_habit",
            "reward",
            "periodicity",
            "duration",
            "is_public",
            "created_at",
            "last_reminder",
        )
        read_only_fields = ("owner", "created_at", "last_reminder")
        validators = [
            RewardOrRelatedHabitValidator(),
            PleasantHabitValidator(),
            RelatedHabitValidator(),
        ]
