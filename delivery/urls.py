from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from orders.views import order_stats

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # API (DRF + JWT) — остаётся для внешних клиентов
    path('api/token/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/', include('users.urls')),
    path('api/', include('products.urls')),
    path('api/', include('orders.urls')),
    path('api/', include('analytics.urls')),
    path('api/orders/stats/', order_stats),

    # Веб-интерфейс (Django Templates)
    path('', include('web.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
