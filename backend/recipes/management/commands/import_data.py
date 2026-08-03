"""Команда импорта ингредиентов и тегов из CSV в базу данных."""

import csv

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient, Tag

DATA_DIR = settings.BASE_DIR / "data"


class Command(BaseCommand):
    help = "Импорт ингредиентов и тегов из CSV в базу данных"

    def _import(self, filename, model, fields, label):
        """Загружает один CSV-файл в указанную модель."""
        try:
            csv_file = open(DATA_DIR / filename, encoding="utf-8")
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Файл {filename} не найден."))
            return
        with csv_file:
            for row in csv.reader(csv_file):
                model.objects.get_or_create(**dict(zip(fields, row)))
        self.stdout.write(self.style.SUCCESS(f"{label} успешно загружены!"))

    def handle(self, *args, **kwargs):
        """Загружает ингредиенты и теги из CSV-файлов."""
        self._import(
            "ingredients.csv",
            Ingredient,
            ("name", "measurement_unit"),
            "Ингредиенты",
        )
        self._import(
            "tags.csv", Tag, ("name", "color", "slug"), "Теги"
        )
