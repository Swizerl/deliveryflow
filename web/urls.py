from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('menu/', views.menu, name='menu'),

    path('login/', views.login_view, name='login_view'),
    path('register/', views.register_view, name='register_view'),
    path('logout/', views.logout_view, name='logout_view'),

    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('cart/checkout/', views.checkout, name='checkout'),

    path('orders/', views.orders_list, name='orders_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),

    path('chat/', views.chat_start, name='chat_start'),
    path('chat/create/', views.chat_create, name='chat_create'),
    path('chat/list/', views.chat_list, name='chat_list'),
    path('chat/<int:room_id>/', views.chat_room, name='chat_room'),

    # Уведомления (JSON API для колокольчика)
    path('notifications/api/', views.notifications_api, name='notifications_api'),
    path('notifications/read/', views.notifications_mark_read, name='notifications_mark_read'),
    path('notifications/', views.notifications_page, name='notifications_page'),

    path('admin-panel/menu/', views.admin_menu, name='admin_menu'),
    path('admin-panel/menu/add/', views.admin_menu_add, name='admin_menu_add'),
    path('admin-panel/menu/edit/<int:product_id>/', views.admin_menu_edit, name='admin_menu_edit'),
    path('admin-panel/menu/delete/<int:product_id>/', views.admin_menu_delete, name='admin_menu_delete'),
    path('admin-panel/analytics/', views.admin_analytics, name='admin_analytics'),
]
