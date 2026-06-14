from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdminRole, user_is_admin
from .dashboard import ANALYTICS_DASHBOARD_KEY, build_dashboard_stats
from .tasks import schedule_analytics_refresh


class AnalyticsDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        if not user_is_admin(request.user):
            return Response({'detail': 'Доступ только для администратора.'}, status=403)

        try:
            cached = cache.get(ANALYTICS_DASHBOARD_KEY)
            if cached is None:
                data = build_dashboard_stats()
                cache.set(ANALYTICS_DASHBOARD_KEY, data, timeout=300)
            else:
                data = cached

            schedule_analytics_refresh()
            return Response({'status': 'ready', 'data': data})
        except Exception as exc:
            return Response(
                {'detail': f'Ошибка формирования статистики: {exc}'},
                status=500,
            )
