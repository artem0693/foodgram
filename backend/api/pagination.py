"""Кастомный класс пагинации."""

from rest_framework.pagination import PageNumberPagination


class PageLimitPagination(PageNumberPagination):
    """Кастомный класс пагинации с поддержкой лимита."""

    page_size_query_param = 'limit'
    page_size = 6
