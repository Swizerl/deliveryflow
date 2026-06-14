from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import serializers

from analytics.dashboard import build_dashboard_stats
from chat.models import ChatRoom, ChatMessage
from chat.tasks import mark_messages_read
from notifications.models import Notification
from notifications.tasks import get_unread_count, invalidate_unread
from orders.events import order_created_event
from orders.models import Order, OrderItem
from orders.realtime import broadcast_order_status, invalidate_order_stats_cache, invalidate_products_cache, MENU_PAGE_CACHE_KEY
from products.events import menu_changed_event
from products.models import Product
from users.models import UserProfile
from users.permissions import user_is_admin, user_is_moderator, user_is_staff, get_user_role


def global_context(request):
    cart = request.session.get('cart', {})
    cart_count = sum(cart.values()) if cart else 0
    is_admin = is_moderator = is_staff = False
    notif_count = 0
    if request.user.is_authenticated:
        # Одна загрузка роли вместо трёх обращений к Redis/БД на каждый запрос.
        role = get_user_role(request.user)
        is_admin = role == UserProfile.ROLE_ADMIN
        is_moderator = role == UserProfile.ROLE_MODERATOR
        is_staff = role in (UserProfile.ROLE_ADMIN, UserProfile.ROLE_MODERATOR)
        notif_count = get_unread_count(request.user.id)
    return {
        'cart_count': cart_count, 'is_admin': is_admin,
        'is_moderator': is_moderator, 'is_staff': is_staff,
        'notif_count': notif_count,
    }


def home(request):
    return render(request, 'home.html')


def menu(request):
    from django.core.cache import cache
    categories = cache.get(MENU_PAGE_CACHE_KEY)
    if categories is None:
        products = list(Product.objects.all())
        categories = []
        for code, label in Product.CATEGORY_CHOICES:
            items = [p for p in products if p.category == code]
            if items:
                categories.append((code, label, items))
        # TTL — подстраховка; реальная инвалидация идёт через invalidate_products_cache()
        # при любом изменении товара или остатка.
        cache.set(MENU_PAGE_CACHE_KEY, categories, timeout=60)
    return render(request, 'menu.html', {'categories': categories})


# ── Авторизация ──

def login_view(request):
    if request.user.is_authenticated:
        return redirect('menu')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username', '').strip(), password=request.POST.get('password', ''))
        if user:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect(request.GET.get('next', 'menu'))
        return render(request, 'login.html', {'error': 'Неверный логин или пароль'})
    return render(request, 'login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('menu')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        if not username or not password:
            return render(request, 'register.html', {'error': 'Заполните все поля'})
        if password != password2:
            return render(request, 'register.html', {'error': 'Пароли не совпадают'})
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Пользователь уже существует'})
        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.get_or_create(user=user, defaults={'role': UserProfile.ROLE_USER})
        login(request, user)
        messages.success(request, 'Регистрация прошла успешно!')
        return redirect('menu')
    return render(request, 'register.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('home')


# ── Корзина ──

@login_required
def cart(request):
    cd = request.session.get('cart', {})
    items, total = [], Decimal('0')
    if cd:
        # Одним запросом вместо отдельного SELECT на каждую позицию корзины.
        ids = []
        for pid in cd.keys():
            try:
                ids.append(int(pid))
            except (ValueError, TypeError):
                continue
        products = {p.id: p for p in Product.objects.filter(id__in=ids)}
        for pid_str, qty in cd.items():
            try:
                p = products.get(int(pid_str))
            except (ValueError, TypeError):
                p = None
            if p is None:
                continue
            lt = p.price * qty
            total += lt
            items.append({'product': p, 'quantity': qty, 'line_total': lt})
    return render(request, 'cart.html', {'items': items, 'total': total})


@login_required
def cart_add(request, product_id):
    p = get_object_or_404(Product, id=product_id)
    cd = request.session.get('cart', {})
    k = str(product_id)
    cur = cd.get(k, 0)
    if cur + 1 > p.stock:
        messages.error(request, f'Недостаточно «{p.name}» на складе')
    else:
        cd[k] = cur + 1
        request.session['cart'] = cd
        messages.success(request, f'«{p.name}» добавлен в корзину')
    return redirect(request.META.get('HTTP_REFERER', 'menu'))


@login_required
def cart_update(request, product_id):
    cd = request.session.get('cart', {})
    try:
        qty = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        qty = 1
    if qty <= 0:
        cd.pop(str(product_id), None)
    else:
        cd[str(product_id)] = qty
    request.session['cart'] = cd
    return redirect('cart')


@login_required
def cart_remove(request, product_id):
    cd = request.session.get('cart', {})
    cd.pop(str(product_id), None)
    request.session['cart'] = cd
    return redirect('cart')


@login_required
def checkout(request):
    if request.method != 'POST':
        return redirect('cart')
    cd = request.session.get('cart', {})
    if not cd:
        messages.error(request, 'Корзина пуста')
        return redirect('cart')
    from django.db import transaction
    try:
        with transaction.atomic():
            order = Order.objects.create(user=request.user)
            for pid_str, qty in cd.items():
                p = Product.objects.get(id=int(pid_str))
                OrderItem.objects.create(order=order, product=p, quantity=qty)
                if not Product.objects.filter(id=p.id, stock__gte=qty).update(stock=F('stock') - qty):
                    raise serializers.ValidationError(f'Недостаточно «{p.name}» на складе.')
            invalidate_products_cache()
    except Exception as exc:
        messages.error(request, f'Ошибка: {exc}')
        return redirect('cart')
    request.session['cart'] = {}
    invalidate_order_stats_cache()
    broadcast_order_status(order)
    order_created_event(order.id)
    messages.success(request, f'Заказ #{order.id} оформлен!')
    return redirect('order_detail', order_id=order.id)


# ── Заказы ──

@login_required
def orders_list(request):
    see_all = user_is_staff(request.user)
    qs = Order.objects.prefetch_related('items__product')
    orders = qs.all() if see_all else qs.filter(user=request.user)
    return render(request, 'orders.html', {'orders': orders, 'can_see_all': see_all})


@login_required
def order_detail(request, order_id):
    qs = Order.objects.prefetch_related('items__product')
    order = get_object_or_404(qs, id=order_id) if user_is_staff(request.user) else get_object_or_404(qs, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})


# ── Чат ──

@login_required
def chat_start(request):
    active_room = ChatRoom.objects.filter(user=request.user, is_active=True).first()
    return render(request, 'chat_start.html', {'active_room': active_room})


@login_required
def chat_create(request):
    if request.method != 'POST':
        return redirect('chat_start')
    active = ChatRoom.objects.filter(user=request.user, is_active=True).first()
    if active:
        return redirect('chat_room', room_id=active.id)
    text = request.POST.get('text', '').strip()
    if not text:
        messages.error(request, 'Введите сообщение')
        return redirect('chat_start')
    room = ChatRoom.objects.create(user=request.user)
    ChatMessage.objects.create(room=room, sender=request.user, text=text)
    from chat.tasks import process_chat_message
    process_chat_message.delay(room.id, request.user.id, text)
    # Уведомить модераторов о новом чате через RabbitMQ → Celery.
    from notifications.tasks import notify_new_chat_for_moderators
    notify_new_chat_for_moderators.delay(room.id, request.user.username)
    return redirect('chat_room', room_id=room.id)


@login_required
def chat_list(request):
    if not user_is_staff(request.user):
        return redirect('home')
    from django.core.cache import cache
    from chat.tasks import UNREAD_COUNT_KEY
    rooms = ChatRoom.objects.filter(is_active=True).select_related('user', 'moderator')
    for room in rooms:
        room.last_msg = room.messages.order_by('-created_at').first()
        room.unread = cache.get(UNREAD_COUNT_KEY.format(room_id=room.id, user_id=request.user.id), 0)
    return render(request, 'chat_list.html', {'rooms': rooms})


@login_required
def chat_room(request, room_id):
    room = get_object_or_404(ChatRoom.objects.select_related('user', 'moderator'), id=room_id)
    staff = user_is_staff(request.user)
    if not staff and room.user != request.user:
        return redirect('home')
    if staff and room.moderator is None:
        room.moderator = request.user
        room.save(update_fields=['moderator'])
    mark_messages_read.delay(room.id, request.user.id)
    return render(request, 'chat_room.html', {'room': room, 'is_staff': staff})


# ── Уведомления (колокольчик) ──

@login_required
def notifications_api(request):
    """JSON API для dropdown колокольчика."""
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:15]
    data = [
        {
            'id': n.id,
            'type': n.notification_type,
            'title': n.title,
            'message': n.message,
            'link': n.link,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%d.%m %H:%M'),
        }
        for n in notifs
    ]
    return JsonResponse({'notifications': data, 'unread': get_unread_count(request.user.id)})


@login_required
def notifications_mark_read(request):
    """Отметить все как прочитанные."""
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        invalidate_unread(request.user.id)
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def notifications_page(request):
    """Полная страница уведомлений."""
    notifs = Notification.objects.filter(user=request.user)[:50]
    return render(request, 'notifications.html', {'notifs': notifs})


# ── Админ: меню ──

@login_required
def admin_menu(request):
    if not user_is_admin(request.user):
        messages.error(request, 'Доступ только для администратора')
        return redirect('home')
    products = Product.objects.all()
    edit_product = None
    edit_id = request.GET.get('edit')
    if edit_id:
        edit_product = Product.objects.filter(id=edit_id).first()
    return render(request, 'admin_menu.html', {'products': products, 'edit_product': edit_product, 'category_choices': Product.CATEGORY_CHOICES})


@login_required
def admin_menu_add(request):
    if not user_is_admin(request.user):
        return redirect('home')
    if request.method == 'POST':
        p = Product.objects.create(name=request.POST['name'], description=request.POST.get('description', ''), category=request.POST.get('category', Product.CATEGORY_HOT), price=request.POST['price'], weight=request.POST.get('weight', ''), stock=request.POST.get('stock', 0))
        if 'image' in request.FILES:
            p.image = request.FILES['image']
            p.save()
        menu_changed_event('created', p.id, request.user.id)
        messages.success(request, f'Товар «{p.name}» добавлен')
    return redirect('admin_menu')


@login_required
def admin_menu_edit(request, product_id):
    if not user_is_admin(request.user):
        return redirect('home')
    p = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        p.name = request.POST['name']
        p.description = request.POST.get('description', '')
        p.category = request.POST.get('category', p.category)
        p.price = request.POST['price']
        p.weight = request.POST.get('weight', '')
        p.stock = request.POST.get('stock', 0)
        if 'image' in request.FILES:
            p.image = request.FILES['image']
        p.save()
        menu_changed_event('updated', p.id, request.user.id)
        messages.success(request, f'Товар «{p.name}» обновлён')
    return redirect('admin_menu')


@login_required
def admin_menu_delete(request, product_id):
    if not user_is_admin(request.user):
        return redirect('home')
    p = get_object_or_404(Product, id=product_id)
    name, pid = p.name, p.id
    p.delete()
    menu_changed_event('deleted', pid, request.user.id)
    messages.success(request, f'Товар «{name}» удалён')
    return redirect('admin_menu')


# ── Аналитика ──

@login_required
def admin_analytics(request):
    if not user_is_staff(request.user):
        return redirect('home')
    from django.core.cache import cache
    from analytics.dashboard import ANALYTICS_DASHBOARD_KEY
    from analytics.tasks import schedule_analytics_refresh
    # Читаем готовую статистику из Redis. Тяжёлый пересчёт (десятки агрегаций)
    # выполняем синхронно только при холодном промахе кэша; в остальных случаях
    # запускаем фоновое обновление с троттлингом, не блокируя запрос.
    data = cache.get(ANALYTICS_DASHBOARD_KEY)
    if data is None:
        try:
            data = build_dashboard_stats()
            cache.set(ANALYTICS_DASHBOARD_KEY, data, timeout=300)
        except Exception:
            data = None
    else:
        schedule_analytics_refresh()
    logs = None
    if user_is_admin(request.user):
        from analytics.models import AnalyticsEvent
        logs = list(AnalyticsEvent.objects.select_related('user').order_by('-created_at')[:50].values('id', 'event_type', 'payload', 'user__username', 'created_at'))
    return render(request, 'admin_analytics.html', {'data': data, 'logs': logs})
