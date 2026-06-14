import datetime

from django.db.models import Count, Sum, F, Avg, DecimalField
from django.db.models.functions import Coalesce, TruncDate, ExtractHour
from django.utils import timezone

from .models import AnalyticsEvent

ANALYTICS_DASHBOARD_KEY = 'analytics:dashboard'


def build_dashboard_stats():
    from orders.models import Order, OrderItem
    from products.models import Product

    today = timezone.localdate()
    now = timezone.now()

    # ── Основные метрики ──

    total_orders = Order.objects.count()
    orders_today = Order.objects.filter(created_at__date=today).count()

    status_rows = Order.objects.values('status').annotate(count=Count('id'))
    orders_by_status = {row['status']: row['count'] for row in status_rows}

    of = DecimalField()

    revenue_total = OrderItem.objects.aggregate(
        total=Coalesce(Sum(F('quantity') * F('product__price'), output_field=of), 0, output_field=of),
    )['total']

    revenue_today = OrderItem.objects.filter(order__created_at__date=today).aggregate(
        total=Coalesce(Sum(F('quantity') * F('product__price'), output_field=of), 0, output_field=of),
    )['total']

    avg_order = 0
    if total_orders > 0:
        avg_order = float(revenue_total or 0) / total_orders

    products_count = Product.objects.count()
    low_stock = Product.objects.filter(stock__lte=5).count()

    # ── Заказы и выручка по дням (14 дней) ──

    start_date = today - datetime.timedelta(days=13)
    daily_orders_qs = (
        Order.objects.filter(created_at__date__gte=start_date)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    daily_orders_map = {row['day']: row['count'] for row in daily_orders_qs}

    daily_revenue_qs = (
        OrderItem.objects.filter(order__created_at__date__gte=start_date)
        .annotate(day=TruncDate('order__created_at'))
        .values('day')
        .annotate(total=Coalesce(
            Sum(F('quantity') * F('product__price'), output_field=of), 0, output_field=of,
        ))
        .order_by('day')
    )
    daily_revenue_map = {row['day']: float(row['total']) for row in daily_revenue_qs}

    date_labels = []
    orders_by_day = []
    revenue_by_day = []
    for i in range(14):
        d = start_date + datetime.timedelta(days=i)
        date_labels.append(d.strftime('%d.%m'))
        orders_by_day.append(daily_orders_map.get(d, 0))
        revenue_by_day.append(daily_revenue_map.get(d, 0))

    # ── Распределение заказов по часам (все время) ──

    hourly_qs = (
        Order.objects.annotate(hour=ExtractHour('created_at'))
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('hour')
    )
    hourly_map = {row['hour']: row['count'] for row in hourly_qs}
    orders_by_hour = [hourly_map.get(h, 0) for h in range(24)]

    # ── Выручка по категориям ──

    category_qs = (
        OrderItem.objects.values('product__category')
        .annotate(total=Coalesce(
            Sum(F('quantity') * F('product__price'), output_field=of), 0, output_field=of,
        ))
        .order_by('-total')
    )
    category_labels_map = dict(Product.CATEGORY_CHOICES)
    category_revenue = [
        {
            'category': category_labels_map.get(row['product__category'], row['product__category']),
            'total': float(row['total']),
        }
        for row in category_qs if row['total']
    ]

    # ── Топ-5 товаров ──

    top_products = []
    for row in (
        OrderItem.objects.values('product__name')
        .annotate(
            sold=Coalesce(Sum('quantity'), 0),
            revenue=Coalesce(
                Sum(F('quantity') * F('product__price'), output_field=of), 0, output_field=of,
            ),
        )
        .order_by('-sold')[:5]
    ):
        top_products.append({
            'product__name': row['product__name'],
            'sold': int(row['sold'] or 0),
            'revenue': float(row['revenue'] or 0),
        })

    # ── Последние события ──

    recent_events = []
    for event in (
        AnalyticsEvent.objects.select_related('user')
        .order_by('-created_at')[:15]
    ):
        recent_events.append({
            'id': event.id,
            'event_type': event.event_type,
            'payload': event.payload,
            'created_at': event.created_at.isoformat(),
            'user__username': event.user.username if event.user else None,
        })

    # ── Статистика чатов ──

    try:
        from chat.models import ChatRoom, ChatMessage
        chat_stats = {
            'total_rooms': ChatRoom.objects.count(),
            'active_rooms': ChatRoom.objects.filter(is_active=True).count(),
            'total_messages': ChatMessage.objects.count(),
            'messages_today': ChatMessage.objects.filter(created_at__date=today).count(),
        }
    except Exception:
        chat_stats = {'total_rooms': 0, 'active_rooms': 0, 'total_messages': 0, 'messages_today': 0}

    return {
        # Метрики
        'total_orders': total_orders,
        'orders_today': orders_today,
        'orders_by_status': orders_by_status,
        'revenue_total': float(revenue_total or 0),
        'revenue_today': float(revenue_today or 0),
        'avg_order': round(avg_order, 0),
        'products_count': products_count,
        'low_stock_count': low_stock,
        # Графики
        'date_labels': date_labels,
        'orders_by_day': orders_by_day,
        'revenue_by_day': revenue_by_day,
        'orders_by_hour': orders_by_hour,
        'category_revenue': category_revenue,
        'top_products': top_products,
        # Чаты
        'chat_stats': chat_stats,
        # События
        'recent_events': recent_events,
        'menu_changes': AnalyticsEvent.objects.filter(event_type=AnalyticsEvent.EVENT_MENU).count(),
        'updated_at': now.isoformat(),
    }
