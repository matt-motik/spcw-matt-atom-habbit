"""Модели приложения users."""

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from users.managers import CustomUserManager


class CustomUser(AbstractUser):
    """Кастомная модель пользователя с авторизацией по email."""

    username = None
    email = models.EmailField(unique=True, verbose_name="Email")
    tg_chat_id = models.CharField(
        max_length=50,
        blank=True,
        validators=[RegexValidator(r"^-?\d+$", "Chat ID Telegram состоит только из цифр.")],
        verbose_name="Chat ID в Telegram",
        help_text="Куда бот присылает напоминания о привычках.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = CustomUserManager()

    class Meta:
        """Мета-параметры модели CustomUser."""

        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        """Возвращает email пользователя."""
        return str(self.email)
