"""Маршруты приложения users."""

from django.urls import path

from users.views import UserProfileAPIView, UserRegisterAPIView, UserTokenObtainPairView, UserTokenRefreshView

app_name = "users"

urlpatterns = [
    path("register/", UserRegisterAPIView.as_view(), name="register"),
    path("token/", UserTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", UserTokenRefreshView.as_view(), name="token-refresh"),
    path("me/", UserProfileAPIView.as_view(), name="profile"),
]
