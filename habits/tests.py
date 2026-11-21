"""Тесты приложения habits: модель и валидаторы привычки."""

from datetime import time
from typing import Any

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, APITestCase

from habits.models import Habit
from habits.serializers import HabitSerializer
from habits.validators import validate_duration, validate_periodicity
from users.models import CustomUser


class HabitsTestCase(APITestCase):
    """Общие тестовые данные: два пользователя, полезная и приятная привычки."""

    def setUp(self) -> None:
        """Создаёт пользователей и привычки."""
        self.user = CustomUser.objects.create_user(email="user@test.ru", password="pass12345", tg_chat_id="123456")
        self.other = CustomUser.objects.create_user(email="other@test.ru", password="pass12345")

        self.pleasant = Habit.objects.create(
            owner=self.user,
            action="принять ванну с пеной",
            time=time(21, 0),
            place="дома",
            is_pleasant=True,
            duration=60,
        )
        self.useful = Habit.objects.create(
            owner=self.user,
            action="гулять вокруг квартала",
            time=time(20, 0),
            place="на улице",
            related_habit=self.pleasant,
            duration=120,
        )
        self.other_pleasant = Habit.objects.create(
            owner=self.other, action="съесть десерт", time=time(19, 0), place="в кафе", is_pleasant=True, duration=60
        )

    def habit_data(self, **kwargs: Any) -> dict[str, Any]:
        """Данные для создания полезной привычки с вознаграждением."""
        data = {
            "action": "делать зарядку",
            "time": "08:00",
            "place": "дома",
            "reward": "чашка кофе",
            "duration": 90,
        }
        data.update(kwargs)
        return data

    def get_serializer(self, data: dict[str, Any], instance: Habit | None = None) -> HabitSerializer:
        """Сериализатор с запросом от первого пользователя в контексте."""
        request = APIRequestFactory().post("/")
        request.user = self.user
        return HabitSerializer(instance, data=data, partial=instance is not None, context={"request": request})

    def assert_invalid(self, serializer: HabitSerializer, field: str = "non_field_errors") -> None:
        """Проверяет, что сериализатор не прошёл валидацию по указанному полю."""
        self.assertFalse(serializer.is_valid())
        self.assertIn(field, serializer.errors)


class HabitModelTestCase(HabitsTestCase):
    """Модель привычки."""

    def test_str(self) -> None:
        """Привычка выводится в формате из книги."""
        self.assertEqual(str(self.useful), "Я буду гулять вокруг квартала в 20:00 в на улице")

    def test_defaults(self) -> None:
        """По умолчанию привычка ежедневная, полезная и не публичная."""
        self.assertEqual(self.useful.periodicity, 1)
        self.assertFalse(self.useful.is_pleasant)
        self.assertFalse(self.useful.is_public)


class FieldValidatorsTestCase(SimpleTestCase):
    """Валидаторы полей: время на выполнение и периодичность."""

    def test_duration(self) -> None:
        """Время на выполнение — от 1 до 120 секунд."""
        validate_duration(1)
        validate_duration(120)
        for value in (0, 121):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_duration(value)

    def test_periodicity(self) -> None:
        """Периодичность — от 1 до 7 дней."""
        validate_periodicity(1)
        validate_periodicity(7)
        for value in (0, 8, 14):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_periodicity(value)


class HabitValidatorsTestCase(HabitsTestCase):
    """Валидаторы привычки в сериализаторе."""

    def test_valid_with_reward(self) -> None:
        """Полезная привычка с вознаграждением проходит валидацию."""
        self.assertTrue(self.get_serializer(self.habit_data()).is_valid())

    def test_valid_with_related_habit(self) -> None:
        """Полезная привычка со своей приятной привычкой проходит валидацию."""
        serializer = self.get_serializer(self.habit_data(reward="", related_habit=self.pleasant.pk))
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_duration_too_long(self) -> None:
        """Время на выполнение больше 120 секунд не проходит."""
        self.assert_invalid(self.get_serializer(self.habit_data(duration=121)), "duration")

    def test_periodicity_too_rare(self) -> None:
        """Привычку нельзя выполнять реже раза в 7 дней."""
        self.assert_invalid(self.get_serializer(self.habit_data(periodicity=8)), "periodicity")

    def test_reward_and_related_habit(self) -> None:
        """Нельзя указать вознаграждение и связанную привычку одновременно."""
        self.assert_invalid(self.get_serializer(self.habit_data(related_habit=self.pleasant.pk)))

    def test_related_habit_not_pleasant(self) -> None:
        """Связанной может быть только приятная привычка."""
        serializer = self.get_serializer(self.habit_data(reward="", related_habit=self.useful.pk))
        self.assert_invalid(serializer, "related_habit")

    def test_related_habit_other_owner(self) -> None:
        """Нельзя связать чужую приятную привычку."""
        serializer = self.get_serializer(self.habit_data(reward="", related_habit=self.other_pleasant.pk))
        self.assert_invalid(serializer, "related_habit")

    def test_related_habit_self(self) -> None:
        """Привычка не может быть связана сама с собой, даже если сейчас она приятная."""
        habit = Habit.objects.create(
            owner=self.user, action="слушать музыку", time=time(18, 0), place="дома", is_pleasant=True, duration=60
        )
        serializer = self.get_serializer({"is_pleasant": False, "related_habit": habit.pk}, habit)
        self.assert_invalid(serializer, "related_habit")

    def test_pleasant_with_reward(self) -> None:
        """У приятной привычки не может быть вознаграждения."""
        self.assert_invalid(self.get_serializer(self.habit_data(is_pleasant=True)))

    def test_pleasant_with_related_habit(self) -> None:
        """У приятной привычки не может быть связанной привычки."""
        serializer = self.get_serializer(self.habit_data(is_pleasant=True, reward="", related_habit=self.pleasant.pk))
        self.assert_invalid(serializer)

    def test_partial_update_uses_instance(self) -> None:
        """При частичном изменении учитываются уже сохранённые поля: вознаграждение к связанной не добавить."""
        self.assert_invalid(self.get_serializer({"reward": "десерт"}, self.useful))

    def test_unset_pleasant_when_linked(self) -> None:
        """Нельзя снять признак приятной, если привычка связана с полезной."""
        self.assert_invalid(self.get_serializer({"is_pleasant": False}, self.pleasant), "is_pleasant")

    def test_unset_pleasant_when_not_linked(self) -> None:
        """Признак приятной снимается, если привычка ни к чему не привязана."""
        self.assertTrue(self.get_serializer({"is_pleasant": False}, self.other_pleasant).is_valid())
