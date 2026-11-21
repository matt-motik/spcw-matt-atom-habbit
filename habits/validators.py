"""Валидаторы приложения habits."""

from collections.abc import Callable
from typing import Any

from django.core.exceptions import ValidationError
from rest_framework import serializers

MAX_DURATION = 120
MAX_PERIODICITY = 7

FieldGetter = Callable[[str], Any]


def validate_duration(value: int) -> None:
    """Время на выполнение — от 1 до 120 секунд."""
    if not 0 < value <= MAX_DURATION:
        raise ValidationError(f"Время на выполнение должно быть от 1 до {MAX_DURATION} секунд.")


def validate_periodicity(value: int) -> None:
    """Привычку нужно выполнять хотя бы раз в 7 дней."""
    if not 0 < value <= MAX_PERIODICITY:
        raise ValidationError(f"Периодичность должна быть от 1 до {MAX_PERIODICITY} дней.")


class HabitValidator:
    """Базовый валидатор привычки: при частичном изменении недостающие поля берутся из объекта."""

    requires_context = True

    def __call__(self, attrs: dict[str, Any], serializer: serializers.Serializer) -> None:
        """Собирает итоговые значения полей и передаёт их в проверку."""
        instance = serializer.instance

        def get(field: str) -> Any:
            if field in attrs:
                return attrs[field]
            return getattr(instance, field, None)

        self.validate(get, serializer)

    def validate(self, get: FieldGetter, serializer: serializers.Serializer) -> None:
        """Проверка, которую реализует конкретный валидатор."""
        raise NotImplementedError


class RewardOrRelatedHabitValidator(HabitValidator):
    """Нельзя одновременно указать вознаграждение и связанную привычку."""

    def validate(self, get: FieldGetter, serializer: serializers.Serializer) -> None:
        """Проверяет, что заполнено не больше одного из двух полей."""
        if get("reward") and get("related_habit"):
            raise serializers.ValidationError("Укажите либо вознаграждение, либо связанную привычку, но не оба сразу.")


class RelatedHabitValidator(HabitValidator):
    """Связанной может быть только своя приятная привычка, но не она сама."""

    def validate(self, get: FieldGetter, serializer: serializers.Serializer) -> None:
        """Проверяет признак приятной привычки, владельца и ссылку на саму себя."""
        related = get("related_habit")
        if related is None:
            return
        if not related.is_pleasant:
            raise serializers.ValidationError({"related_habit": "Связанной может быть только приятная привычка."})
        request = serializer.context.get("request")
        if request is not None and related.owner_id != request.user.pk:
            raise serializers.ValidationError({"related_habit": "Связанной может быть только своя привычка."})
        if serializer.instance is not None and related.pk == serializer.instance.pk:
            raise serializers.ValidationError({"related_habit": "Привычка не может быть связана сама с собой."})


class PleasantHabitValidator(HabitValidator):
    """У приятной привычки нет вознаграждения и связанной привычки."""

    def validate(self, get: FieldGetter, serializer: serializers.Serializer) -> None:
        """Проверяет приятную привычку и запрет снимать признак, если она уже к чему-то привязана."""
        instance = serializer.instance
        if get("is_pleasant"):
            if get("reward") or get("related_habit"):
                raise serializers.ValidationError(
                    "У приятной привычки не может быть вознаграждения или связанной привычки."
                )
        elif instance is not None and instance.is_pleasant and instance.linked_habits.exists():
            raise serializers.ValidationError(
                {"is_pleasant": "Привычка связана с полезными привычками и должна оставаться приятной."}
            )
