from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserProfile
from .serializers import UserMeSerializer


class RegisterView(APIView):
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Укажите логин и пароль'}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Пользователь уже существует'}, status=400)

        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.get_or_create(user=user, defaults={'role': UserProfile.ROLE_USER})

        return Response({'message': 'Пользователь создан'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # select_related('profile') — избегаем лишних запросов в сериализаторе.
        user = User.objects.select_related('profile').get(pk=request.user.pk)
        return Response(UserMeSerializer(user).data)
