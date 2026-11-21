"""Пагинация приложения habits."""

from rest_framework.pagination import LimitOffsetPagination


class HabitPaginator(LimitOffsetPagination):
    """Списки привычек: по 5 на страницу, не больше 50 за запрос."""

    default_limit = 5
    max_limit = 50
