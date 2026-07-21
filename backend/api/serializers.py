"""Сериализаторы для приложения api."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from users.models import Follow

User = get_user_model()


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингредиентов."""

    class Meta:
        """Метаданные сериализатора ингредиента."""

        model = Ingredient
        fields = "__all__"


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели тегов."""

    class Meta:
        """Метаданные сериализатора тега."""

        model = Tag
        fields = ("id", "name", "slug")


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        """Метаданные сериализатора пользователя."""

        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        )

    def get_is_subscribed(self, author):
        """Проверка подписки текущего пользователя на автора."""
        request = self.context.get("request")
        return (
            request is not None
            and request.user.is_authenticated
            and request.user.follower.filter(author=author).exists()
        )


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения ингредиентов внутри рецепта."""

    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.CharField(source="ingredient.name", read_only=True)
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit", read_only=True
    )
    amount = serializers.ReadOnlyField()

    class Meta:
        """Метаданные сериализатора ингредиентов в рецепте."""

        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Сериализатор для связи ингредиента и его количества."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        """Метаданные сериализатора количества ингредиентов."""

        model = RecipeIngredient
        fields = ("id", "amount")


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецепта."""

    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True, source="ingredient_list", read_only=True
    )
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)

    class Meta:
        """Метаданные сериализатора чтения рецепта."""

        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецепта."""

    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    ingredients = IngredientAmountSerializer(many=True, allow_empty=False)
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), allow_empty=False
    )
    image = Base64ImageField()

    class Meta:
        """Метаданные сериализатора записи рецепта."""

        model = Recipe
        fields = (
            "author",
            "ingredients",
            "tags",
            "image",
            "name",
            "text",
            "cooking_time",
        )

    def validate_image(self, value):
        """Запрещает пустое изображение."""
        if not value:
            raise serializers.ValidationError("Нужно добавить изображение.")
        return value

    def validate_ingredients(self, ingredients):
        """Проверяет, что ингредиенты не повторяются."""
        ids = [ingredient_data["id"] for ingredient_data in ingredients]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться."
            )
        return ingredients

    def validate_tags(self, tags):
        """Проверяет, что теги не повторяются."""
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError("Теги не должны повторяться.")
        return tags

    def _create_ingredients(self, recipe, ingredients):
        """Вспомогательный метод для создания ингредиентов."""
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data["id"],
                amount=ingredient_data["amount"],
            )
            for ingredient_data in ingredients
        )

    @transaction.atomic
    def create(self, validated_data):
        """Создание нового рецепта."""
        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        recipe = super().create(validated_data)
        recipe.tags.set(tags)
        self._create_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        """Обновление существующего рецепта."""
        ingredients = validated_data.pop("ingredients", None)
        tags = validated_data.pop("tags", None)
        if tags is not None:
            instance.tags.set(tags)
        if ingredients is not None:
            instance.ingredients.clear()
            self._create_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Преобразование объекта в JSON-формат."""
        user = self.context["request"].user
        instance = Recipe.objects.with_user_flags(user).get(pk=instance.pk)
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого представления рецепта."""

    class Meta:
        """Метаданные сериализатора короткого рецепта."""

        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class BaseFavoriteCartSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для избранного и списка покупок."""

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        """Общие метаданные: пользователь и рецепт."""

        fields = ("user", "recipe")

    def to_representation(self, instance):
        """Возвращает краткое представление рецепта."""
        return RecipeShortSerializer(
            instance.recipe, context=self.context
        ).data


class FavoriteSerializer(BaseFavoriteCartSerializer):
    """Сериализатор добавления рецепта в избранное."""

    class Meta(BaseFavoriteCartSerializer.Meta):
        """Метаданные сериализатора избранного."""

        model = Favorite
        validators = (
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=("user", "recipe"),
                message="Рецепт уже в избранном.",
            ),
        )


class ShoppingCartSerializer(BaseFavoriteCartSerializer):
    """Сериализатор добавления рецепта в список покупок."""

    class Meta(BaseFavoriteCartSerializer.Meta):
        """Метаданные сериализатора списка покупок."""

        model = ShoppingCart
        validators = (
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=("user", "recipe"),
                message="Рецепт уже в списке покупок.",
            ),
        )


class SubscribeSerializer(serializers.ModelSerializer):
    """Сериализатор создания подписки на автора."""

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        """Метаданные сериализатора подписки."""

        model = Follow
        fields = ("user", "author")
        validators = (
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=("user", "author"),
                message="Вы уже подписаны на этого автора.",
            ),
        )

    def validate_author(self, author):
        """Запрещает подписку на самого себя."""
        if self.context["request"].user == author:
            raise serializers.ValidationError(
                "Нельзя подписаться на самого себя."
            )
        return author

    def to_representation(self, instance):
        """Возвращает данные автора со списком его рецептов."""
        return SubscriptionSerializer(
            instance.author, context=self.context
        ).data


class SetPasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля."""

    new_password = serializers.CharField(write_only=True)
    current_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        """Проверка текущего пароля."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль.")
        return value

    def validate_new_password(self, value):
        """Валидация нового пароля."""
        validate_password(value, user=self.context["request"].user)
        return value

    def create(self, validated_data):
        """Установка нового пароля."""
        user = self.context["request"].user
        user.set_password(validated_data["new_password"])
        user.save()
        return user


class SetAvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара."""

    avatar = Base64ImageField()

    class Meta:
        """Метаданные сериализатора аватара."""

        model = User
        fields = ("avatar",)


class SubscriptionSerializer(UserSerializer):
    """Сериализатор для подписок."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source="recipes.count", read_only=True
    )

    class Meta(UserSerializer.Meta):
        """Метаданные сериализатора подписок."""

        fields = UserSerializer.Meta.fields + ("recipes", "recipes_count")

    def get_recipes(self, author):
        """Получение списка рецептов автора для подписки."""
        request = self.context.get("request")
        recipes = author.recipes.all()
        limit = request.query_params.get("recipes_limit") if request else None
        if limit:
            try:
                recipes = recipes[: int(limit)]
            except ValueError:
                pass
        return RecipeShortSerializer(
            recipes, many=True, context=self.context
        ).data
