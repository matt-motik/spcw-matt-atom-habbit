"""Контроллеры приложения users."""

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from config.schema import UNAUTHORIZED, VALIDATION_ERROR
from users.models import CustomUser
from users.serializers import UserProfileSerializer, UserRegisterSerializer


@extend_schema(
    tags=["Пользователи"],
    summary="Регистрация",
    description="Доступна без авторизации. Email должен быть свободен, пароль проверяется валидаторами Django. "
    "tg_chat_id можно указать сразу или позже в профиле: без него напоминания не приходят.",
    responses={201: UserRegisterSerializer, 400: VALIDATION_ERROR},
)
class UserRegisterAPIView(generics.CreateAPIView):
    """Регистрация нового пользователя. Доступна без авторизации."""

    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = (AllowAny,)


@extend_schema(
    tags=["Авторизация"],
    summary="Получение токенов",
    description="Возвращает пару access / refresh по email и паролю. Доступно без авторизации.",
    responses={
        200: inline_serializer(
            name="TokenPair",
            fields={"access": serializers.CharField(), "refresh": serializers.CharField()},
        ),
        400: VALIDATION_ERROR,
        401: OpenApiResponse(description="Неверный email или пароль."),
    },
)
class UserTokenObtainPairView(TokenObtainPairView):
    """Получение пары JWT-токенов. Доступно без авторизации."""


@extend_schema(
    tags=["Авторизация"],
    summary="Обновление access-токена",
    description="Возвращает новый access по refresh-токену. Доступно без авторизации.",
    responses={
        200: inline_serializer(name="AccessToken", fields={"access": serializers.CharField()}),
        400: VALIDATION_ERROR,
        401: OpenApiResponse(description="Refresh-токен недействителен или истёк."),
    },
)
class UserTokenRefreshView(TokenRefreshView):
    """Обновление access-токена по refresh. Доступно без авторизации."""


@extend_schema(tags=["Пользователи"])
@extend_schema_view(
    get=extend_schema(
        summary="Свой профиль",
        responses={200: UserProfileSerializer, 401: UNAUTHORIZED},
    ),
    put=extend_schema(
        summary="Изменение своего профиля",
        description="Email не меняется. Здесь же задаётся tg_chat_id для напоминаний.",
        responses={200: UserProfileSerializer, 400: VALIDATION_ERROR, 401: UNAUTHORIZED},
    ),
    patch=extend_schema(
        summary="Частичное изменение своего профиля",
        description="Email не меняется. Здесь же задаётся tg_chat_id для напоминаний.",
        responses={200: UserProfileSerializer, 400: VALIDATION_ERROR, 401: UNAUTHORIZED},
    ),
)
class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """Просмотр и изменение профиля текущего пользователя."""

    serializer_class = UserProfileSerializer

    def get_object(self) -> CustomUser:
        """Возвращает текущего пользователя."""
        user: CustomUser = self.request.user  # type: ignore[assignment]
        return user
