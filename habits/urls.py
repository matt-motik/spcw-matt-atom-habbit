"""Маршруты приложения habits."""

from django.urls import path
from rest_framework.routers import SimpleRouter

from habits.views import HabitViewSet, PublicHabitListAPIView

app_name = "habits"

router = SimpleRouter()
router.register("", HabitViewSet, basename="habits")

# Публичный список идёт до router.urls: иначе "public" совпадёт с шаблоном /habits/<pk>/
urlpatterns = [
    path("public/", PublicHabitListAPIView.as_view(), name="public"),
] + router.urls
