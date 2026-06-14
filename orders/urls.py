from django.urls import path
from .views import CreateOrderView, OrderDetailView, OrderListView

urlpatterns = [
    path('orders/', OrderListView.as_view()),
    path('orders/<int:pk>/', OrderDetailView.as_view()),
    path('orders/create/', CreateOrderView.as_view()),
]
