"""Кастомные права доступа."""

from rest_framework.permissions import SAFE_METHODS, IsAuthenticatedOrReadOnly


class IsAuthenticatedAuthorOrReadOnly(IsAuthenticatedOrReadOnly):
    """Чтение — всем, изменение — только автору объекта.

    Наследуется от IsAuthenticatedOrReadOnly: has_permission уже запрещает
    небезопасные методы неаутентифицированным пользователям.
    """

    def has_object_permission(self, request, view, recipe):
        """Разрешает изменение объекта только его автору."""
        return request.method in SAFE_METHODS or recipe.author == request.user
