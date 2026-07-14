from django.contrib import admin
from django.db import models
from .models import Recipe, Ingredient, Tag, Favorite, ShoppingCart, RecipeIngredient

class RecipeIngredientInline(admin.TabularInline):
    """Инлайн для отображения ингредиентов внутри рецепта."""
    model = RecipeIngredient
    extra = 1
    min_num = 1

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Админка для тегов."""
    list_display = ('name', 'slug')
    search_fields = ('name',)

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Админка для ингредиентов."""
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Админка для рецептов."""
    list_display = ('name', 'author', 'count_favorites')
    # Фильтруем только по тем полям, где выпадающий список оправдан
    list_filter = ('author', 'tags')
    # Добавляем поиск по названию
    search_fields = ('name', 'author__username')
    inlines = (RecipeIngredientInline,)

    def get_queryset(self, request):
        """Оптимизация запроса: считаем избранное одним SQL-запросом."""
        return super().get_queryset(request).annotate(
            favorites_count=models.Count('favorites')
        )

    def count_favorites(self, obj):
        """Выводим аннотированное значение."""
        return obj.favorites_count
    
    count_favorites.short_description = 'В избранном'

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')

@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')