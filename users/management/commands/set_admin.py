from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from users.models import UserProfile


class Command(BaseCommand):
    help = 'Назначить пользователю роль администратора (role=admin)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)

    def handle(self, *args, **options):
        username = options['username']
        user = User.objects.get(username=username)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.ROLE_ADMIN
        profile.save(update_fields=['role'])
        self.stdout.write(self.style.SUCCESS(f'Пользователь {username} — администратор'))
