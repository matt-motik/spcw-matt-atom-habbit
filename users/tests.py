"""Тесты приложения users: регистрация, JWT, профиль, менеджер пользователей."""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import CustomUser

CREDENTIALS = {"email": "user@test.ru", "password": "pass12345"}


class UsersTestCase(APITestCase):
    """Общие тестовые данные: пользователь с chat_id."""

    def setUp(self) -> None:
        """Создаёт пользователя."""
        self.user = CustomUser.objects.create_user(**CREDENTIALS, tg_chat_id="123456")


class RegisterTestCase(UsersTestCase):
    """Регистрация пользователя."""

    def test_register(self) -> None:
        """Регистрация доступна без авторизации, пароль хешируется."""
        data = {"email": "new@test.ru", "password": "Strong-pass-42", "tg_chat_id": "987654"}
        response = self.client.post(reverse("users:register"), data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.json())
        user = CustomUser.objects.get(email="new@test.ru")
        self.assertTrue(user.check_password("Strong-pass-42"))
        self.assertEqual(user.tg_chat_id, "987654")

    def test_register_existing_email(self) -> None:
        """Нельзя зарегистрироваться с уже занятым email."""
        data = {"email": "USER@test.ru", "password": "Strong-pass-42"}
        response = self.client.post(reverse("users:register"), data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json())

    def test_register_weak_password(self) -> None:
        """Слабый пароль не проходит валидацию."""
        data = {"email": "new@test.ru", "password": "123"}
        response = self.client.post(reverse("users:register"), data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.json())
        self.assertFalse(CustomUser.objects.filter(email="new@test.ru").exists())

    def test_register_wrong_chat_id(self) -> None:
        """Chat ID Telegram состоит только из цифр."""
        data = {"email": "new@test.ru", "password": "Strong-pass-42", "tg_chat_id": "abc"}
        response = self.client.post(reverse("users:register"), data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tg_chat_id", response.json())


class TokenTestCase(UsersTestCase):
    """Получение и обновление JWT."""

    def test_token_obtain_and_refresh(self) -> None:
        """По email и паролю выдаётся пара токенов, refresh обновляет access."""
        response = self.client.post(reverse("users:token-obtain-pair"), CREDENTIALS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tokens = response.json()
        self.assertIn("access", tokens)

        response = self.client.post(reverse("users:token-refresh"), {"refresh": tokens["refresh"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.json())

    def test_token_wrong_password(self) -> None:
        """С неверным паролем токен не выдаётся."""
        response = self.client.post(reverse("users:token-obtain-pair"), {"email": "user@test.ru", "password": "wrong"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_with_token(self) -> None:
        """С access-токеном в заголовке доступен профиль."""
        response = self.client.post(reverse("users:token-obtain-pair"), CREDENTIALS)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")

        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["email"], "user@test.ru")


class UserProfileTestCase(UsersTestCase):
    """Профиль текущего пользователя."""

    def test_profile(self) -> None:
        """Профиль отдаётся без пароля."""
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("users:profile"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["tg_chat_id"], "123456")
        self.assertNotIn("password", response.json())

    def test_profile_anonymous(self) -> None:
        """Без авторизации профиль недоступен."""
        response = self.client.get(reverse("users:profile"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile(self) -> None:
        """В профиле меняется chat_id, email остаётся прежним."""
        self.client.force_authenticate(self.user)
        response = self.client.patch(reverse("users:profile"), {"tg_chat_id": "-100500", "email": "x@test.ru"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.tg_chat_id, "-100500")
        self.assertEqual(self.user.email, "user@test.ru")


class CustomUserManagerTestCase(TestCase):
    """Создание пользователей через менеджер."""

    def test_create_user_without_email(self) -> None:
        """Без email пользователь не создаётся."""
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(email="", password="pass12345")

    def test_create_superuser(self) -> None:
        """Суперпользователь получает права администратора."""
        admin = CustomUser.objects.create_superuser(email="admin@test.ru", password="pass12345")

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(str(admin), "admin@test.ru")

    def test_create_superuser_wrong_flags(self) -> None:
        """Суперпользователь не создаётся без is_staff или is_superuser."""
        for flag in ("is_staff", "is_superuser"):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                CustomUser.objects.create_superuser(email="admin@test.ru", password="pass12345", **{flag: False})
