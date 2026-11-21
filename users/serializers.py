"""Сериализаторы приложения users."""

from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import serializers

from users.models import CustomUser


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля текущего пользователя."""

    class Meta:
        """Мета-параметры сериализатора профиля."""

        model = CustomUser
        fields = ("id", "email", "first_name", "last_name", "tg_chat_id")
        read_only_fields = ("id", "email")


class UserRegisterSerializer(serializers.ModelSerializer):
    """Сериализатор регистрации пользователя."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    email = serializers.EmailField()

    class Meta:
        """Мета-параметры сериализатора регистрации."""

        model = CustomUser
        fields = ("id", "email", "password", "first_name", "last_name", "tg_chat_id")

    def validate_email(self, value: str) -> str:
        """Проверяет, что пользователь с таким email ещё не зарегистрирован."""
        email = value.strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return email

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Проверяет пароль стандартными валидаторами Django."""
        user = CustomUser(**{key: value for key, value in attrs.items() if key != "password"})
        try:
            validate_password(attrs["password"], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        return attrs

    def create(self, validated_data: dict[str, Any]) -> CustomUser:
        """Создаёт пользователя с хешированным паролем."""
        try:
            user: CustomUser = CustomUser.objects.create_user(**validated_data)
        except (ValueError, IntegrityError) as error:
            raise serializers.ValidationError({"detail": "Не удалось создать пользователя."}) from error
        return user
