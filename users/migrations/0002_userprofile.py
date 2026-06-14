import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_profiles_for_existing_users(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('users', 'UserProfile')
    for user in User.objects.all():
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.is_superuser or user.is_staff:
            profile.role = 'admin'
            profile.save(update_fields=['role'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[('user', 'Пользователь'), ('admin', 'Администратор')],
                    default='user',
                    max_length=20,
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Профиль',
                'verbose_name_plural': 'Профили',
            },
        ),
        migrations.RunPython(create_profiles_for_existing_users, migrations.RunPython.noop),
    ]
