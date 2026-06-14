from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware:
    """
    JWT-аутентификация для WebSocket.
    Приоритет: subprotocol «bearer.<token>», fallback — query string ?token=<token>.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()
        token = None

        # 1. Пробуем достать токен из subprotocols (безопаснее — не попадает в логи).
        subprotocols = scope.get("subprotocols", [])
        for sp in subprotocols:
            if sp.startswith("bearer."):
                token = sp[len("bearer."):]
                break

        # 2. Fallback: query string (?token=...) для обратной совместимости.
        if not token:
            query_string = scope.get("query_string", b"").decode()
            token = parse_qs(query_string).get("token", [None])[0]

        if token:
            try:
                validated = AccessToken(token)
                scope["user"] = await get_user(validated["user_id"])
            except (InvalidToken, TokenError, KeyError):
                pass

        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
