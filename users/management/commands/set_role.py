from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from users.models import UserProfile
from users.permissions import invalidate_role_cache


class Command(BaseCommand):
    help = (
        'Назначить роль пользователю.\n'
        'Использование: python manage.py set_role <username> <role>\n'
        'Роли: user, moderator, admin'
    )

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument(
            'role',
            type=str,
            choices=[UserProfile.ROLE_USER, UserProfile.ROLE_MODERATOR, UserProfile.ROLE_ADMIN],
        )

    def handle(self, *args, **options):
        username = options['username']
        role = options['role']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'Пользователь «{username}» не найден.')

        profile, _ = UserProfile.objects.get_or_create(user=user)
        old_role = profile.role
        profile.role = role
        profile.save(update_fields=['role'])

        # Инвалидируем Redis-кэш роли.
        invalidate_role_cache(user.pk)

        # Асинхронно логируем смену роли через RabbitMQ → Celery.
        try:
            from analytics.tasks import log_role_change
            log_role_change.delay(user.pk, old_role, role)
        except Exception:
            pass  # Celery/RabbitMQ недоступен — не блокируем команду.

        role_display = dict(UserProfile.ROLE_CHOICES).get(role, role)
        self.stdout.write(
            self.style.SUCCESS(f'{username} → {role_display}')
        )
