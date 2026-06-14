from django.urls import path

from .views import AnalyticsDashboardView

urlpatterns = [
    path('analytics/dashboard/', AnalyticsDashboardView.as_view()),
]
