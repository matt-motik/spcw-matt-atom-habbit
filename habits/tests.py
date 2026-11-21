"""Тесты приложения habits: модель, валидаторы, эндпоинты, права доступа, пагинация и напоминания."""

from datetime import date, datetime, time
from typing import Any
from unittest import mock

import requests
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from habits.models import Habit
from habits.serializers import HabitSerializer
from habits.services import build_reminder, get_habits_to_remind, send_telegram_message
from habits.tasks import send_habit_reminders
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
        self.assertEqual(str(self.useful), "Я буду гулять вокруг квартала в 20:00 на улице")

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


class HabitCRUDTestCase(HabitsTestCase):
    """CRUD своих привычек."""

    def setUp(self) -> None:
        """Авторизует первого пользователя."""
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_list_only_own(self) -> None:
        """В списке только свои привычки."""
        response = self.client.get(reverse("habits:habits-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {habit["id"] for habit in response.json()["results"]}
        self.assertEqual(ids, {self.pleasant.pk, self.useful.pk})

    def test_create(self) -> None:
        """Создателем привычки становится текущий пользователь, даже если передан другой."""
        response = self.client.post(reverse("habits:habits-list"), self.habit_data(owner=self.other.pk))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        habit = Habit.objects.get(pk=response.json()["id"])
        self.assertEqual(habit.owner, self.user)
        self.assertEqual(habit.periodicity, 1)

    def test_create_invalid(self) -> None:
        """Ошибки валидаторов возвращаются с кодом 400."""
        response = self.client.post(reverse("habits:habits-list"), self.habit_data(duration=300))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("duration", response.json())

    def test_retrieve(self) -> None:
        """Своя привычка доступна для просмотра."""
        response = self.client.get(reverse("habits:habits-detail", args=[self.useful.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["related_habit"], self.pleasant.pk)

    def test_update(self) -> None:
        """Свою привычку можно изменить."""
        response = self.client.patch(reverse("habits:habits-detail", args=[self.useful.pk]), {"place": "в парке"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.useful.refresh_from_db()
        self.assertEqual(self.useful.place, "в парке")

    def test_delete(self) -> None:
        """Свою привычку можно удалить, связь у полезной при этом обнуляется."""
        response = self.client.delete(reverse("habits:habits-detail", args=[self.pleasant.pk]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Habit.objects.filter(pk=self.pleasant.pk).exists())
        self.useful.refresh_from_db()
        self.assertIsNone(self.useful.related_habit)

    def test_other_habit_not_available(self) -> None:
        """Чужая привычка не видна, не изменяется и не удаляется, даже публичная."""
        self.other_pleasant.is_public = True
        self.other_pleasant.save()
        url = reverse("habits:habits-detail", args=[self.other_pleasant.pk])

        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.patch(url, {"place": "дома"}).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Habit.objects.filter(pk=self.other_pleasant.pk).exists())

    def test_anonymous(self) -> None:
        """Без авторизации привычки недоступны."""
        self.client.force_authenticate(None)

        self.assertEqual(self.client.get(reverse("habits:habits-list")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(reverse("habits:public")).status_code, status.HTTP_401_UNAUTHORIZED)


class PublicHabitTestCase(HabitsTestCase):
    """Список публичных привычек."""

    def test_public_list(self) -> None:
        """В списке публичные привычки всех пользователей, включая свои."""
        Habit.objects.filter(pk__in=[self.useful.pk, self.other_pleasant.pk]).update(is_public=True)
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("habits:public"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {habit["id"] for habit in response.json()["results"]}
        self.assertEqual(ids, {self.useful.pk, self.other_pleasant.pk})

    def test_public_read_only(self) -> None:
        """Публичный список только для чтения."""
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("habits:public"), self.habit_data())

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class PaginationTestCase(HabitsTestCase):
    """Пагинация: по 5 привычек, limit и offset."""

    def setUp(self) -> None:
        """Добавляет первому пользователю ещё 10 публичных привычек."""
        super().setUp()
        Habit.objects.bulk_create(
            Habit(owner=self.user, action=f"привычка {i}", time=time(9, 0), place="дома", duration=30, is_public=True)
            for i in range(10)
        )
        self.client.force_authenticate(self.user)

    def test_default_limit(self) -> None:
        """По умолчанию отдаётся 5 привычек, count — общее количество."""
        for url in (reverse("habits:habits-list"), reverse("habits:public")):
            with self.subTest(url=url):
                data = self.client.get(url).json()
                self.assertEqual(len(data["results"]), 5)
                self.assertIsNotNone(data["next"])
                self.assertIsNone(data["previous"])

        self.assertEqual(self.client.get(reverse("habits:habits-list")).json()["count"], 12)
        self.assertEqual(self.client.get(reverse("habits:public")).json()["count"], 10)

    def test_limit_offset(self) -> None:
        """Limit и offset сдвигают окно выборки, limit ограничен 50."""
        data = self.client.get(reverse("habits:habits-list"), {"limit": 3, "offset": 10}).json()
        self.assertEqual(len(data["results"]), 2)
        self.assertIsNone(data["next"])

        data = self.client.get(reverse("habits:habits-list"), {"limit": 100}).json()
        self.assertEqual(len(data["results"]), 12)


def moscow(hour: int, minute: int = 0, day: int = 10) -> datetime:
    """Момент времени 2026-11-{day} в часовом поясе проекта."""
    moment: datetime = timezone.make_aware(datetime(2026, 11, day, hour, minute))
    return moment


class HabitsToRemindTestCase(HabitsTestCase):
    """Выбор привычек для напоминания."""

    def test_time_has_come(self) -> None:
        """Напоминание приходит, когда наступило время полезной привычки; приятные не напоминаются."""
        self.assertEqual(get_habits_to_remind(moscow(19, 59)), [])
        self.assertEqual(get_habits_to_remind(moscow(21, 30)), [self.useful])

    def test_without_chat_id(self) -> None:
        """Пользователю без chat_id напоминания не отправляются."""
        self.user.tg_chat_id = ""
        self.user.save()

        self.assertEqual(get_habits_to_remind(moscow(21)), [])

    def test_periodicity(self) -> None:
        """Повторное напоминание приходит не раньше, чем через periodicity дней."""
        self.useful.periodicity = 3
        self.useful.last_reminder = date(2026, 11, 10)
        self.useful.save()

        for day, expected in ((10, []), (11, []), (12, []), (13, [self.useful])):
            with self.subTest(day=day):
                self.assertEqual(get_habits_to_remind(moscow(20, day=day)), expected)


class BuildReminderTestCase(HabitsTestCase):
    """Текст напоминания."""

    def test_with_related_habit(self) -> None:
        """В напоминании есть привычка, время на выполнение и приятная привычка."""
        text = build_reminder(self.useful)

        self.assertIn("Напоминание: я буду гулять вокруг квартала в 20:00 на улице.", text)
        self.assertIn("120 сек", text)
        self.assertIn("принять ванну с пеной", text)

    def test_with_reward(self) -> None:
        """Если связанной привычки нет, в напоминании указано вознаграждение."""
        self.useful.related_habit = None
        self.useful.reward = "чашка кофе"

        self.assertIn("Награда: чашка кофе", build_reminder(self.useful))


@override_settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_API_URL="https://api.telegram.test")
class SendTelegramMessageTestCase(SimpleTestCase):
    """Отправка сообщения в Telegram."""

    @mock.patch("habits.services.requests.post")
    def test_send(self, post: mock.Mock) -> None:
        """Сообщение уходит методом sendMessage с chat_id и текстом."""
        self.assertTrue(send_telegram_message("123456", "Привет"))

        post.assert_called_once_with(
            "https://api.telegram.test/bottest-token/sendMessage",
            json={"chat_id": "123456", "text": "Привет"},
            timeout=10,
        )

    @mock.patch("habits.services.requests.post")
    def test_telegram_error(self, post: mock.Mock) -> None:
        """Ошибка Telegram не роняет отправку, а возвращает False и пишется в лог без токена."""
        post.return_value.raise_for_status.side_effect = requests.HTTPError("403 for url with test-token")

        with self.assertLogs("habits.services", level="ERROR") as logs:
            self.assertFalse(send_telegram_message("123456", "Привет"))
        self.assertNotIn("test-token", logs.output[0])

    @override_settings(TELEGRAM_BOT_TOKEN="")
    @mock.patch("habits.services.requests.post")
    def test_without_token(self, post: mock.Mock) -> None:
        """Без токена бота запрос в Telegram не отправляется."""
        with self.assertLogs("habits.services", level="WARNING"):
            self.assertFalse(send_telegram_message("123456", "Привет"))
        post.assert_not_called()


class SendHabitRemindersTaskTestCase(HabitsTestCase):
    """Задача Celery для рассылки напоминаний."""

    @mock.patch("habits.tasks.timezone.localtime", return_value=moscow(20, 1))
    @mock.patch("habits.tasks.send_telegram_message", return_value=True)
    def test_sends_and_marks(self, send: mock.Mock, localtime: mock.Mock) -> None:
        """Задача отправляет напоминание владельцу и запоминает дату, второй запуск в тот же день ничего не шлёт."""
        self.assertEqual(send_habit_reminders(), 1)
        send.assert_called_once_with("123456", build_reminder(self.useful))
        self.useful.refresh_from_db()
        self.assertEqual(self.useful.last_reminder, date(2026, 11, 10))

        self.assertEqual(send_habit_reminders(), 0)
        send.assert_called_once()

    @mock.patch("habits.tasks.timezone.localtime", return_value=moscow(20, 1))
    @mock.patch("habits.tasks.send_telegram_message", return_value=False)
    def test_failed_send_retries(self, send: mock.Mock, localtime: mock.Mock) -> None:
        """Если отправка не удалась, дата не запоминается и напоминание повторится при следующем запуске."""
        self.assertEqual(send_habit_reminders(), 0)
        self.useful.refresh_from_db()
        self.assertIsNone(self.useful.last_reminder)
