"""Представления для пользователей, ингредиентов, тегов и рецептов."""

from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import UserCreateSerializer
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

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


class UserViewSet(viewsets.ModelViewSet):
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

    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор для действия."""
        serializers_by_action = {
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
        serializer = self.get_serializer(data={"author": author.pk})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, pk=None):
        """Отписаться от автора."""
        author = self.get_object()
        deleted, _ = request.user.follower.filter(author=author).delete()
        if not deleted:
            raise ValidationError("Вы не были подписаны на этого автора.")
        return Response(status=status.HTTP_204_NO_CONTENT)

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


class RecipeViewSet(viewsets.ModelViewSet):
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

    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор для действия."""
        if self.action == "favorite":
            return FavoriteSerializer
        if self.action == "shopping_cart":
            return ShoppingCartSerializer
        if self.action in ("list", "retrieve"):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def update(self, request, *args, **kwargs):
        """Обновление рецепта: все поля обязательны, в том числе при PATCH."""
        kwargs["partial"] = False
        return super().update(request, *args, **kwargs)

    def _add_relation(self, pk):
        """Добавляет рецепт в избранное или список покупок."""
        get_object_or_404(Recipe, pk=pk)
        serializer = self.get_serializer(data={"recipe": pk})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _remove_relation(self, model, pk):
        """Удаляет рецепт из избранного или списка покупок."""
        get_object_or_404(Recipe, pk=pk)
        deleted, _ = model.objects.filter(
            user=self.request.user, recipe_id=pk
        ).delete()
        if not deleted:
            raise ValidationError("Рецепта не было в списке.")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=("post",),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        """Добавляет рецепт в избранное."""
        return self._add_relation(pk)

    @favorite.mapping.delete
    def remove_favorite(self, request, pk=None):
        """Удаляет рецепт из избранного."""
        return self._remove_relation(Favorite, pk)

    @action(
        detail=True,
        methods=("post",),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def shopping_cart(self, request, pk=None):
        """Добавляет рецепт в список покупок."""
        return self._add_relation(pk)

    @shopping_cart.mapping.delete
    def remove_shopping_cart(self, request, pk=None):
        """Удаляет рецепт из списка покупок."""
        return self._remove_relation(ShoppingCart, pk)

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
        body = "\n".join(
            f"{product['name']} ({product['unit']}) — {product['total']}"
            for product in products
        )
        response = HttpResponse(
            f"Список покупок:\n\n{body}",
            content_type="text/plain; charset=utf-8",
        )
        response["Content-Disposition"] = (
            'attachment; filename="shopping_cart.txt"'
        )
        return response

    @action(detail=True, url_path="get-link")
    def get_link(self, request, pk=None):
        """Генерирует короткую ссылку на рецепт."""
        self.get_object()
        short_link = request.build_absolute_uri(
            reverse("short-link", args=(pk,))
        )
        return Response({"short-link": short_link})
