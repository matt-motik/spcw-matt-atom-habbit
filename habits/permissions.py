"""Классы прав доступа приложения habits."""

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsOwner(BasePermission):
    """Пользователь является создателем привычки."""

    message = "Действие доступно только создателю привычки."

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        """Проверяет, что привычка принадлежит текущему пользователю."""
        return bool(obj.owner == request.user)
