import logging

from django.core.cache import cache
from rest_framework.permissions import BasePermission

from .models import UserProfile

logger = logging.getLogger(__name__)

ROLE_CACHE_KEY = 'user_role:{}'
ROLE_CACHE_TTL = 300  # 5 минут


def _get_user_role(user):
    """
    Возвращает роль пользователя. Результат кэшируется в Redis,
    чтобы не обращаться к БД при каждом запросе.
    """
    if not user or not user.is_authenticated:
        return UserProfile.ROLE_USER

    cache_key = ROLE_CACHE_KEY.format(user.pk)
    role = cache.get(cache_key)
    if role is not None:
        return role

    profile = UserProfile.objects.filter(user_id=user.pk).values_list('role', flat=True).first()
    role = profile or UserProfile.ROLE_USER
    cache.set(cache_key, role, ROLE_CACHE_TTL)
    return role


def invalidate_role_cache(user_id):
    """Инвалидирует Redis-кэш роли при смене роли."""
    cache.delete(ROLE_CACHE_KEY.format(user_id))


def user_is_admin(user):
    return _get_user_role(user) == UserProfile.ROLE_ADMIN


def user_is_moderator(user):
    return _get_user_role(user) == UserProfile.ROLE_MODERATOR


def user_is_staff(user):
    """Администратор ИЛИ модератор."""
    return _get_user_role(user) in (UserProfile.ROLE_ADMIN, UserProfile.ROLE_MODERATOR)


def get_user_role(user):
    """Возвращает строковую роль пользователя."""
    return _get_user_role(user)


class IsAdminRole(BasePermission):
    message = 'Доступ только для администратора.'

    def has_permission(self, request, view):
        return user_is_admin(request.user)


class IsStaffRole(BasePermission):
    """Допускает администраторов и модераторов."""
    message = 'Доступ только для администратора или модератора.'

    def has_permission(self, request, view):
        return user_is_staff(request.user)
