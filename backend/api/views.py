"""Представления для пользователей, ингредиентов, тегов и рецептов."""

import io

from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import UserCreateSerializer
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from .filters import IngredientFilter, RecipeFilter
from .pagination import PageLimitPagination
from .permissions import IsAuthenticatedAuthorOrReadOnly
from .serializers import (FavoriteSerializer, IngredientSerializer,
                          RecipeReadSerializer, RecipeWriteSerializer,
                          SetAvatarSerializer, SetPasswordSerializer,
                          ShoppingCartSerializer, SubscribeSerializer,
                          SubscriptionSerializer, TagSerializer,
                          UserSerializer)

User = get_user_model()


class RelationMixin:
    """Общая логика добавления и удаления связи «пользователь — объект».

    Используется для избранного, списка покупок и подписок.
    """

    def create_relation(self, data):
        """Создаёт связь; вся валидация — в сериализаторе действия."""
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_relation(self, queryset, error_message):
        """Удаляет связь; отдаёт 400, если её не существовало."""
        deleted, _ = queryset.delete()
        if not deleted:
            raise ValidationError(error_message)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserViewSet(RelationMixin, viewsets.ModelViewSet):
    """ViewSet для работы с пользователями."""

    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    http_method_names = (
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
    )

    def get_permissions(self):
        """Возвращает права доступа в зависимости от действия."""
        if self.action in {"update", "partial_update", "destroy"}:
            return (permissions.IsAuthenticated(),)
        return super().get_permissions()

    def get_serializer_class(self) -> type[BaseSerializer]:
        """Возвращает соответствующий сериализатор для действия."""
        serializers_by_action: dict[str, type[BaseSerializer]] = {
            "create": UserCreateSerializer,
            "set_password": SetPasswordSerializer,
            "avatar": SetAvatarSerializer,
            "subscribe": SubscribeSerializer,
            "subscriptions": SubscriptionSerializer,
        }
        return serializers_by_action.get(self.action, UserSerializer)

    @action(detail=False, permission_classes=(permissions.IsAuthenticated,))
    def me(self, request):
        """Возвращает данные текущего пользователя."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=("post",),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def set_password(self, request):
        """Изменяет пароль пользователя."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=("put",),
        url_path="me/avatar",
        permission_classes=(permissions.IsAuthenticated,),
    )
    def avatar(self, request):
        """Устанавливает аватар пользователя."""
        serializer = self.get_serializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаляет аватар пользователя."""
        request.user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=("post",),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def subscribe(self, request, pk=None):
        """Подписаться на автора."""
        author = self.get_object()
        return self.create_relation({"author": author.pk})

    @subscribe.mapping.delete
    def unsubscribe(self, request, pk=None):
        """Отписаться от автора."""
        author = self.get_object()
        return self.delete_relation(
            request.user.follower.filter(author=author),
            "Вы не были подписаны на этого автора.",
        )

    @action(detail=False, permission_classes=(permissions.IsAuthenticated,))
    def subscriptions(self, request):
        """Возвращает список подписок текущего пользователя."""
        authors = User.objects.filter(following__user=request.user)
        page = self.paginate_queryset(authors)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class BaseReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """Базовый вьюсет только для чтения, без пагинации."""

    pagination_class = None


class IngredientViewSet(BaseReadOnlyViewSet):
    """ViewSet для получения списка ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(BaseReadOnlyViewSet):
    """ViewSet для получения списка тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeViewSet(RelationMixin, viewsets.ModelViewSet):
    """ViewSet для управления рецептами."""

    permission_classes = (IsAuthenticatedAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = PageLimitPagination

    def get_queryset(self):
        """Рецепты с флагами избранного и корзины для текущего пользователя."""
        return (
            Recipe.objects.with_user_flags(self.request.user)
            .select_related("author")
            .prefetch_related("tags", "ingredient_list__ingredient")
        )

    def get_serializer_class(self) -> type[BaseSerializer]:
        """Возвращает соответствующий сериализатор для действия."""
        if self.action == "favorite":
            return FavoriteSerializer
        if self.action == "shopping_cart":
            return ShoppingCartSerializer
        if self.action in {"list", "retrieve"}:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def update(self, request, *args, **kwargs):
        """Обновление рецепта: все поля обязательны, в том числе при PATCH."""
        return super().update(request, *args, **{**kwargs, "partial": False})

    @action(
        detail=True,
        methods=("post",),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        """Добавляет рецепт в избранное."""
        get_object_or_404(Recipe, pk=pk)
        return self.create_relation({"recipe": pk})

    @favorite.mapping.delete
    def remove_favorite(self, request, pk=None):
        """Удаляет рецепт из избранного."""
        get_object_or_404(Recipe, pk=pk)
        return self.delete_relation(
            request.user.favorites.filter(recipe_id=pk),
            "Рецепта не было в избранном.",
        )

    @action(
        detail=True,
        methods=("post",),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def shopping_cart(self, request, pk=None):
        """Добавляет рецепт в список покупок."""
        get_object_or_404(Recipe, pk=pk)
        return self.create_relation({"recipe": pk})

    @shopping_cart.mapping.delete
    def remove_shopping_cart(self, request, pk=None):
        """Удаляет рецепт из списка покупок."""
        get_object_or_404(Recipe, pk=pk)
        return self.delete_relation(
            request.user.shopping_cart.filter(recipe_id=pk),
            "Рецепта не было в списке покупок.",
        )

    @action(detail=False, permission_classes=(permissions.IsAuthenticated,))
    def download_shopping_cart(self, request):
        """Формирует и отдаёт файл со списком покупок."""
        products = (
            RecipeIngredient.objects.filter(
                recipe__shopping_cart__user=request.user
            )
            .values(
                name=F("ingredient__name"),
                unit=F("ingredient__measurement_unit"),
            )
            .annotate(total=Sum("amount"))
            .order_by("name")
        )
        lines = [
            f"{product['name']} ({product['unit']}) — {product['total']}"
            for product in products
        ]
        content = "Список покупок:\n\n" + "\n".join(lines)
        return FileResponse(
            io.BytesIO(content.encode("utf-8")),
            as_attachment=True,
            filename="shopping_cart.txt",
            content_type="text/plain; charset=utf-8",
        )

    @action(detail=True, url_path="get-link")
    def get_link(self, request, pk=None):
        """Генерирует короткую ссылку на рецепт."""
        self.get_object()
        short_link = request.build_absolute_uri(
            reverse("short-link", args=(pk,))
        )
        return Response({"short-link": short_link})
