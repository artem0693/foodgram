"""Создание тестовых данных: пользователи и их рецепты."""

from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from PIL import Image

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag

User = get_user_model()

PASSWORD = "PASSWORD1234"

USERS = [
    {
        "username": "admin",
        "email": "admin@foodgram.local",
        "first_name": "Админ",
        "last_name": "Главный",
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "username": "moderator",
        "email": "moderator@foodgram.local",
        "first_name": "Модератор",
        "last_name": "Проверяющий",
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "username": "Артём",
        "email": "artem@foodgram.local",
        "first_name": "Артём",
        "last_name": "Кулинаров",
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "username": "Иван",
        "email": "ivan@foodgram.local",
        "first_name": "Иван",
        "last_name": "Поваров",
        "is_staff": False,
        "is_superuser": False,
    },
]


class Command(BaseCommand):
    help = "Создаёт тестовых пользователей и по рецепту от каждого."

    def make_image(self, name):
        """Создаёт простую картинку-заглушку для рецепта."""
        image = Image.new("RGB", (400, 300), (200, 200, 200))
        buffer = BytesIO()
        image.save(buffer, "PNG")
        return ContentFile(buffer.getvalue(), name=name)

    def handle(self, *args, **options):
        # Если ингредиентов или тегов ещё нет — загружаем их.
        if not Ingredient.objects.exists() or not Tag.objects.exists():
            call_command("import_data")

        tags = list(Tag.objects.all())
        ingredients = list(Ingredient.objects.all()[:3])

        number = 1
        for data in USERS:
            user, created = User.objects.get_or_create(
                username=data["username"], defaults=data
            )
            if created:
                user.set_password(PASSWORD)
                user.save()

            # Создаём рецепт, только если у пользователя его ещё нет.
            if not user.recipes.exists():
                recipe = Recipe.objects.create(
                    author=user,
                    name=f"Блюдо от {user.first_name}",
                    text="Простой и вкусный рецепт для теста.",
                    cooking_time=number * 10,
                )
                recipe.image.save(
                    f"recipe_{number}.png",
                    self.make_image(f"recipe_{number}.png"),
                )
                recipe.tags.set(tags)
                for ingredient in ingredients:
                    RecipeIngredient.objects.create(
                        recipe=recipe, ingredient=ingredient, amount=50
                    )
            number += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Тестовые данные созданы. Пароль у всех: {PASSWORD}"
            )
        )
