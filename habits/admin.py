"""Админка приложения habits."""

from django.contrib import admin

from habits.models import Habit


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    """Настройки админки для привычек."""

    list_display = ("id", "owner", "action", "time", "place", "is_pleasant", "periodicity", "is_public")
    list_filter = ("is_pleasant", "is_public", "periodicity")
    search_fields = ("action", "place", "owner__email")
