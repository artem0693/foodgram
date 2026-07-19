# Foodgram — «Книга рецептов»

Сайт, где пользователи публикуют рецепты, подписываются на авторов, добавляют
рецепты в избранное и скачивают список покупок с нужными ингредиентами.

## Адрес проекта

- Сайт: https://foodgramedaaa.servepics.com/
- Админка: https://foodgramedaaa.servepics.com/admin/
- Документация API: https://foodgramedaaa.servepics.com/api/docs/

## Стек

Python, Django, Django REST Framework, Djoser, PostgreSQL, Gunicorn, Nginx,
Docker, GitHub Actions.

## Запуск проекта

1. Установите Docker и Docker Compose.
2. Создайте в корне проекта файл `.env` (пример полей ниже).
3. Запустите контейнеры:

```bash
docker compose up -d
```

Backend при старте сам применяет миграции и собирает статику. После запуска
наполните базу данными:

```bash
docker compose exec backend python manage.py import_data
docker compose exec backend python manage.py create_testdata
```

### Пример .env

```
SECRET_KEY=ваш-ключ
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,backend,84.252.135.235,foodgramedaaa.servepics.com

POSTGRES_DB=foodgram_db
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=ваш-пароль

DB_HOST=db
DB_PORT=5432
```

## Тестовые пользователи

Команда `create_testdata` создаёт пользователей с разными правами и по рецепту
от каждого. Пароль у всех: `PASSWORD1234`.

| Роль             | Email                    |
|------------------|--------------------------|
| Администратор    | admin@foodgram.local     |
| Модератор        | moderator@foodgram.local |
| Пользователь     | artem@foodgram.local     |
| Пользователь     | ivan@foodgram.local      |

## Деплой

При пуше в ветку `main` GitHub Actions проверяет код линтером flake8, собирает
образы, пушит их в Docker Hub и разворачивает проект на сервере.

## Автор

Артём — [github.com/artem0693](https://github.com/artem0693)

