"""Модели приложения users.

Описывает кастомную модель пользователя и логику подписок на авторов.
"""

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    """Кастомная модель пользователя.

    Вместо username для авторизации используется email.
    """

    email = models.EmailField(
        verbose_name='Адрес электронной почты',
        unique=True,
        max_length=254
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=150
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=150
    )
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='users/',
        null=True,
        blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        """Метаданные модели пользователя."""

        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('id',)

    def __str__(self):
        """Возвращает строковое представление пользователя (email)."""
        return self.email


class Follow(models.Model):
    """Модель системы подписок.

    Связывает пользователя, который подписывается, и автора рецептов.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор'
    )

    def clean(self):
        """Запрещает подписку на самого себя.

        Срабатывает при full_clean() — то есть через ModelForm/админку.
        Основная защита в API — явная проверка в UserViewSet.subscribe,
        эта проверка дополнительно закрывает случай создания записи
        через django admin.
        """
        if self.user_id == self.author_id:
            raise ValidationError('Нельзя подписаться на самого себя.')

    class Meta:
        """Метаданные модели подписок."""

        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_follow'
            ),
            models.CheckConstraint(
                condition=~models.Q(user=models.F('author')),
                name='prevent_self_follow'
            ),
        ]

    def __str__(self):
        """Возвращает информацию о том, кто на кого подписан."""
        return f'{self.user.username} подписан на {self.author.username}'