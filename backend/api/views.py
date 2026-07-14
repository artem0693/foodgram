"""Вьюсеты для API проекта Foodgram."""

from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from users.models import Follow, User

from .filters import IngredientFilter, RecipeFilter
from .pagination import PageLimitPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (IngredientSerializer, RecipeReadSerializer,
                          RecipeShortSerializer, RecipeWriteSerializer,
                          SetAvatarSerializer, SetPasswordSerializer,
                          SubscriptionSerializer, TagSerializer,
                          UserCreateSerializer, UserSerializer)


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет для управления пользователями."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny,)
    http_method_names = ["get", "post", "put", "head", "options"]

    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор для действия."""
        if self.action == "create":
            return UserCreateSerializer
        if self.action == "set_password":
            return SetPasswordSerializer
        if self.action == "avatar":
            return SetAvatarSerializer
        if self.action == "subscribe":
            return SubscriptionSerializer
        return UserSerializer

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def me(self, request):
        """Возвращает информацию о текущем пользователе."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def set_password(self, request):
        """Изменяет пароль пользователя."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["PUT", "DELETE"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="me/avatar",
    )
    def avatar(self, request):
        """Устанавливает или удаляет аватар пользователя."""
        try:
            if request.method == "PUT":
                serializer = SetAvatarSerializer(
                    request.user, data=request.data
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)

            if request.user.avatar:
                request.user.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            raise e

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscribe(self, request, pk=None):
        """Создает или удаляет подписку на автора."""
        author = get_object_or_404(User, pk=pk)
        if request.method == "POST":
            if request.user == author:
                return Response(
                    {"errors": "Нельзя подписаться на себя"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            follow, created = Follow.objects.get_or_create(
                user=request.user, author=author
            )
            if not created:
                return Response(
                    {"errors": "Вы уже подписаны"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = SubscriptionSerializer(
                author, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        deleted, _ = Follow.objects.filter(
            user=request.user, author=author
        ).delete()
        if not deleted:
            return Response(
                {"errors": "Вы не были подписаны"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscriptions(self, request):
        """Возвращает список авторов, на которых подписан пользователь."""
        queryset = User.objects.filter(following__user=request.user).annotate(
            recipes_count=Count("recipes")
        )
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для управления рецептами."""

    queryset = Recipe.objects.select_related("author").prefetch_related(
        "tags", "ingredient_list__ingredient"
    )
    permission_classes = (
        IsAuthorOrReadOnly,
        permissions.IsAuthenticatedOrReadOnly,
    )
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = PageLimitPagination

    def get_serializer_class(self):
        """Возвращает сериализатор в зависимости от действия."""
        if self.action in ("list", "retrieve"):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        """Сохраняет рецепт с текущим автором."""
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        """Добавляет рецепт в избранное или удаляет из него."""
        return self._add_or_remove_related(request, pk, Favorite)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        """Добавляет рецепт в список покупок или удаляет из него."""
        return self._add_or_remove_related(request, pk, ShoppingCart)

    def _add_or_remove_related(self, request, pk, model):
        """Вспомогательный метод для избранного и списка покупок."""
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == "POST":
            if model.objects.filter(user=request.user, recipe=recipe).exists():
                return Response(
                    {"errors": "Рецепт уже добавлен"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            model.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeShortSerializer(
                recipe, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        deleted, _ = model.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {"errors": "Рецепт не найден в списке"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        """Отдаёт .txt файл со списком покупок."""
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__shopping_cart__user=request.user
            )
            .values(
                "ingredient__name",
                "ingredient__measurement_unit",
            )
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        lines = ["Список покупок:", ""]
        for item in ingredients:
            lines.append(
                f"{item['ingredient__name']} "
                f"({item['ingredient__measurement_unit']}) — "
                f"{item['total_amount']}"
            )

        response = HttpResponse(
            "\n".join(lines), content_type="text/plain; charset=utf-8"
        )
        response["Content-Disposition"] = (
            'attachment; filename="shopping_cart.txt"'
        )
        return response

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        """Возвращает короткую неизменяемую ссылку на рецепт."""
        get_object_or_404(Recipe, pk=pk)
        short_link = request.build_absolute_uri(f"/s/{pk}")
        return Response({"short-link": short_link})
