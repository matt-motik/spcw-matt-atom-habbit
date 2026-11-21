"""Контроллеры приложения habits."""

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import BaseSerializer

from config.schema import NOT_FOUND, UNAUTHORIZED, VALIDATION_ERROR, id_parameter
from habits.models import Habit
from habits.paginators import HabitPaginator
from habits.permissions import IsOwner
from habits.serializers import HabitSerializer

HABIT_ID = id_parameter("ID привычки.")

VALIDATION_RULES = (
    "Правила: время на выполнение не больше 120 секунд; периодичность от 1 до 7 дней; "
    "нельзя указать и вознаграждение, и связанную привычку; связанной может быть только своя приятная привычка; "
    "у приятной привычки нет вознаграждения и связанной привычки."
)


@extend_schema(tags=["Привычки"])
@extend_schema_view(
    list=extend_schema(
        summary="Список своих привычек",
        description="Привычки текущего пользователя с пагинацией: limit (по умолчанию 5, не больше 50) и offset.",
        responses={200: HabitSerializer(many=True), 401: UNAUTHORIZED},
    ),
    create=extend_schema(
        summary="Создание привычки",
        description=f"Создателем становится текущий пользователь. {VALIDATION_RULES}",
        responses={201: HabitSerializer, 400: VALIDATION_ERROR, 401: UNAUTHORIZED},
    ),
    retrieve=extend_schema(
        summary="Привычка",
        description="Доступна только своя привычка.",
        parameters=[HABIT_ID],
        responses={200: HabitSerializer, 401: UNAUTHORIZED, 404: NOT_FOUND},
    ),
    update=extend_schema(
        summary="Изменение привычки",
        description=f"Изменить можно только свою привычку. {VALIDATION_RULES}",
        parameters=[HABIT_ID],
        responses={200: HabitSerializer, 400: VALIDATION_ERROR, 401: UNAUTHORIZED, 404: NOT_FOUND},
    ),
    partial_update=extend_schema(
        summary="Частичное изменение привычки",
        description=f"Изменить можно только свою привычку. Незаполненные поля берутся из сохранённой привычки. "
        f"{VALIDATION_RULES}",
        parameters=[HABIT_ID],
        responses={200: HabitSerializer, 400: VALIDATION_ERROR, 401: UNAUTHORIZED, 404: NOT_FOUND},
    ),
    destroy=extend_schema(
        summary="Удаление привычки",
        description="Удалить можно только свою привычку.",
        parameters=[HABIT_ID],
        responses={204: None, 401: UNAUTHORIZED, 404: NOT_FOUND},
    ),
)
class HabitViewSet(viewsets.ModelViewSet):
    """CRUD привычек текущего пользователя."""

    serializer_class = HabitSerializer
    pagination_class = HabitPaginator
    permission_classes = (IsAuthenticated, IsOwner)

    def get_queryset(self) -> QuerySet[Habit]:
        """Возвращает только привычки текущего пользователя."""
        return Habit.objects.filter(owner=self.request.user.pk)

    def perform_create(self, serializer: BaseSerializer) -> None:
        """Делает текущего пользователя создателем привычки."""
        serializer.save(owner=self.request.user)


@extend_schema(
    tags=["Привычки"],
    summary="Список публичных привычек",
    description="Публичные привычки всех пользователей, включая свои, только для просмотра. "
    "Пагинация: limit (по умолчанию 5, не больше 50) и offset.",
    responses={200: HabitSerializer(many=True), 401: UNAUTHORIZED},
)
class PublicHabitListAPIView(generics.ListAPIView):
    """Список публичных привычек без возможности изменения."""

    queryset = Habit.objects.filter(is_public=True)
    serializer_class = HabitSerializer
    pagination_class = HabitPaginator
