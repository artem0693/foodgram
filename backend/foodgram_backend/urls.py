"""Маршрутизация проекта."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import get_object_or_404, redirect
from django.urls import include, path

from recipes.models import Recipe


def short_link_redirect(request, pk):
    """Перенаправляет с короткой ссылки на страницу рецепта фронтенда."""
    get_object_or_404(Recipe, pk=pk)
    return redirect(f"/recipes/{pk}")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("s/<int:pk>/", short_link_redirect, name="short-link"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
