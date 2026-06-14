from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'stock', 'image', 'image_url']
        read_only_fields = ['image_url']

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url
