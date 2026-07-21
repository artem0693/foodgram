"""Админка для приложения recipes."""

from django.contrib import admin
from django.db import models

from .models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Tag)


class NameSearchAdmin(admin.ModelAdmin):
    """Базовая админка с поиском по названию."""

    search_fields = ("name",)


class UserRecipeAdmin(admin.ModelAdmin):
    """Базовая админка для связей пользователь-рецепт."""

    list_display = ("user", "recipe")


class RecipeIngredientInline(admin.TabularInline):
    """Инлайн для отображения ингредиентов внутри рецепта."""

    model = RecipeIngredient
    extra = 1
    min_num = 1


@admin.register(Tag)
class TagAdmin(NameSearchAdmin):
    """Админка для тегов."""

    list_display = ("name", "slug")


@admin.register(Ingredient)
class IngredientAdmin(NameSearchAdmin):
    """Админка для ингредиентов."""

    list_display = ("name", "measurement_unit")


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Админка для рецептов."""

    list_display = ("name", "author", "count_favorites")
    list_filter = ("author", "tags")
    search_fields = ("name", "author__username")
    inlines = (RecipeIngredientInline,)

    def get_queryset(self, request):
        """Оптимизация запроса: считаем избранное одним SQL-запросом."""
        return (
            super()
            .get_queryset(request)
            .annotate(favorites_count=models.Count("favorites"))
        )

    def count_favorites(self, recipe):
        """Выводим аннотированное значение."""
        return recipe.favorites_count

    count_favorites.short_description = "В избранном"


@admin.register(Favorite)
class FavoriteAdmin(UserRecipeAdmin):
    """Админка для избранного."""


@admin.register(ShoppingCart)
class ShoppingCartAdmin(UserRecipeAdmin):
    """Админка для корзины покупок."""
