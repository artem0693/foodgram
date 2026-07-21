"""Фильтры для рецептов."""

from django_filters import rest_framework as filters
from recipes.models import Ingredient, Recipe, Tag


class IngredientFilter(filters.FilterSet):
    """Фильтр ингредиентов по началу названия."""

    name = filters.CharFilter(lookup_expr="istartswith")

    class Meta:
        """Метаданные фильтра ингредиентов."""

        model = Ingredient
        fields = ("name",)


class RecipeFilter(filters.FilterSet):
    """Фильтр для модели Recipe."""

    tags = filters.ModelMultipleChoiceFilter(
        field_name="tags__slug",
        to_field_name="slug",
        queryset=Tag.objects.all(),
    )
    is_favorited = filters.BooleanFilter(field_name="is_favorited")
    is_in_shopping_cart = filters.BooleanFilter(
        field_name="is_in_shopping_cart"
    )

    class Meta:
        """Метаданные фильтра рецептов."""

        model = Recipe
        fields = ("author", "tags", "is_favorited", "is_in_shopping_cart")
