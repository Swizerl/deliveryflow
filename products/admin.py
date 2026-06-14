from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'weight', 'stock')
    list_filter = ('category',)
    search_fields = ('name',)
    list_editable = ('price', 'stock')
