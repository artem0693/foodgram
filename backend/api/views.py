from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import User, Follow
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    IngredientSerializer,
    TagSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    RecipeShortSerializer,
    UserSerializer,
    UserCreateSerializer,
    SetPasswordSerializer,
    SetAvatarSerializer,
    SubscriptionSerializer,
)
from .filters import RecipeFilter, IngredientFilter
from .pagination import PageLimitPagination


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny,)
    http_method_names = ['get', 'post', 'put', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action == 'set_password':
            return SetPasswordSerializer
        if self.action == 'avatar':
            return SetAvatarSerializer
        if self.action == 'subscribe':
            return SubscriptionSerializer
        return UserSerializer

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def set_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
            detail=False, 
            methods=['PUT', 'DELETE'], 
            permission_classes=[permissions.IsAuthenticated],
            url_path='me/avatar'
    )
    def avatar(self, request):
        try:
            if request.method == 'PUT':
                serializer = SetAvatarSerializer(request.user, data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            # DELETE
            if request.user.avatar:
                request.user.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            # Это выведет реальную ошибку в логи Docker
            print(f"CRITICAL ERROR: {e}")
            raise e

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            if request.user == author:
                return Response({'errors': 'Нельзя подписаться на себя'}, status=status.HTTP_400_BAD_REQUEST)
            follow, created = Follow.objects.get_or_create(user=request.user, author=author)
            if not created:
                return Response({'errors': 'Вы уже подписаны'}, status=status.HTTP_400_BAD_REQUEST)
            serializer = SubscriptionSerializer(author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        deleted, _ = Follow.objects.filter(user=request.user, author=author).delete()
        if not deleted:
            return Response({'errors': 'Вы не были подписаны'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(following__user=request.user).annotate(recipes_count=Count('recipes'))
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'ingredient_list__ingredient'
    )
    permission_classes = (IsAuthorOrReadOnly, permissions.IsAuthenticatedOrReadOnly)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = PageLimitPagination

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        return self._add_or_remove_related(request, pk, Favorite)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self._add_or_remove_related(request, pk, ShoppingCart)

    def _add_or_remove_related(self, request, pk, model):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            if model.objects.filter(user=request.user, recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже добавлен'}, status=status.HTTP_400_BAD_REQUEST)
            model.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeShortSerializer(recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        deleted, _ = model.objects.filter(user=request.user, recipe=recipe).delete()
        if not deleted:
            return Response({'errors': 'Рецепт не найден в списке'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        """Отдаёт .txt файл со списком покупок, ингредиенты суммированы."""
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit',
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        lines = ['Список покупок:', '']
        for item in ingredients:
            lines.append(
                f"{item['ingredient__name']} "
                f"({item['ingredient__measurement_unit']}) — "
                f"{item['total_amount']}"
            )

        response = HttpResponse(
            '\n'.join(lines), content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.txt"'
        )
        return response

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        """Возвращает короткую неизменяемую ссылку на рецепт."""
        get_object_or_404(Recipe, pk=pk)
        short_link = request.build_absolute_uri(f'/s/{pk}')
        return Response({'short-link': short_link})