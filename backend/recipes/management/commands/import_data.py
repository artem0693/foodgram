import csv
from django.core.management.base import BaseCommand
from recipes.models import Ingredient, Tag

class Command(BaseCommand):
    help = 'Импорт ингредиентов и тегов из CSV в базу данных'

    def handle(self, *args, **kwargs):
        # 1. Импорт ингредиентов
        try:
            # Используем абсолютный путь внутри контейнера
            with open('/app/data/ingredients.csv', encoding='utf-8') as f:
                reader = csv.reader(f)
                for name, unit in reader:
                    Ingredient.objects.get_or_create(name=name, measurement_unit=unit)
            self.stdout.write(self.style.SUCCESS('Ингредиенты успешно загружены!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при импорте ингредиентов: {e}'))

        # 2. Импорт тегов
        try:
            with open('/app/data/tags.csv', encoding='utf-8') as f:
                reader = csv.reader(f)
                for name, color, slug in reader:
                    Tag.objects.get_or_create(name=name, color=color, slug=slug)
            self.stdout.write(self.style.SUCCESS('Теги успешно загружены!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при импорте тегов: {e}'))
