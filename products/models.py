from django.db import models


class Product(models.Model):
    CATEGORY_ROLLS = 'rolls'
    CATEGORY_HOT = 'hot'
    CATEGORY_SOUPS = 'soups'
    CATEGORY_SALADS = 'salads'
    CATEGORY_APPETIZERS = 'appetizers'
    CATEGORY_DESSERTS = 'desserts'
    CATEGORY_DRINKS = 'drinks'

    CATEGORY_CHOICES = [
        (CATEGORY_ROLLS, '🍣 Роллы и суши'),
        (CATEGORY_HOT, '🔥 Горячие блюда'),
        (CATEGORY_SOUPS, '🍜 Супы'),
        (CATEGORY_SALADS, '🥗 Салаты'),
        (CATEGORY_APPETIZERS, '🥟 Закуски'),
        (CATEGORY_DESSERTS, '🍰 Десерты'),
        (CATEGORY_DRINKS, '🥤 Напитки'),
    ]

    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, default='', verbose_name='Описание')
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_HOT,
        verbose_name='Категория',
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    weight = models.CharField(max_length=50, blank=True, default='', verbose_name='Вес/объём')
    stock = models.PositiveIntegerField(default=0, verbose_name='Остаток')
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Фото')

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name
