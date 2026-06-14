from django.contrib.auth.models import User
from rest_framework import serializers

from .models import UserProfile
from .permissions import get_user_role, user_is_admin, user_is_moderator, user_is_staff


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['role']


class UserMeSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    is_moderator = serializers.SerializerMethodField()
    is_staff = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'is_admin', 'is_moderator', 'is_staff']

    def get_role(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.role if profile else UserProfile.ROLE_USER

    def get_is_admin(self, obj):
        return user_is_admin(obj)

    def get_is_moderator(self, obj):
        return user_is_moderator(obj)

    def get_is_staff(self, obj):
        return user_is_staff(obj)
