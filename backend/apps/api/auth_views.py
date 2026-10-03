from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import effective_staff_permissions

REFRESH_COOKIE = "momand_refresh"
REFRESH_PATH = "/api/v1/auth/"


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Authenticate the store's generated-username accounts by email."""
    username_field = "email"

    def validate(self, attrs):
        email = str(attrs.get("email", "")).strip().lower()
        password = attrs.get("password", "")
        user_model = get_user_model()
        user = user_model.objects.filter(email__iexact=email).first()
        if not user or not user.is_active or not user.check_password(password):
            raise AuthenticationFailed("No active account found with the given credentials.")
        refresh = self.get_token(user)
        self.user = user
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


def attach_refresh_cookie(response, token):
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path=REFRESH_PATH,
    )
    return response


class CookieTokenObtainPairView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = EmailTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = dict(serializer.validated_data)
        refresh = tokens.pop("refresh")
        user = serializer.user
        response = Response({
            "access": tokens["access"],
            "user": {
                "id": user.pk,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "groups": list(user.groups.values_list("name", flat=True)),
                "permissions": effective_staff_permissions(user),
                "can_manage_users": bool(user.is_superuser or user.has_perm("auth.view_user") or user.groups.filter(name__in=("Admin", "Super Admin")).exists()),
            },
        })
        return attach_refresh_cookie(response, refresh)


class CookieTokenRefreshView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        refresh = request.COOKIES.get(REFRESH_COOKIE)
        if not refresh:
            return Response({"detail": "Refresh token is missing."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = TokenRefreshSerializer(data={"refresh": refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, InvalidToken):
            response = Response({"detail": "Refresh token is invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)
            response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)
            return response
        tokens = dict(serializer.validated_data)
        new_refresh = tokens.pop("refresh", None)
        response = Response(tokens)
        if new_refresh:
            attach_refresh_cookie(response, new_refresh)
        return response


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        refresh = request.COOKIES.get(REFRESH_COOKIE)
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)
        return response


class PasswordResetRequestView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        user_model = get_user_model()
        user = user_model.objects.filter(email__iexact=email, is_active=True).first() if email else None
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
            reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"
            send_mail(
                "Reset your Momand Super Store password",
                f"Use this link to reset your password: {reset_url}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        return Response({"detail": "If an account matches that email, a password reset link has been sent."})


class ConfirmPasswordResetView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        password = request.data.get("password")
        if not uid or not token or not password:
            return Response({"detail": "uid, token, and password are required."}, status=400)
        user_model = get_user_model()
        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = user_model.objects.get(pk=user_id)
        except (ValueError, TypeError, OverflowError, user_model.DoesNotExist):
            return Response({"detail": "Invalid password reset link."}, status=400)
        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired password reset link."}, status=400)
        from django.contrib.auth.password_validation import validate_password
        from rest_framework.exceptions import ValidationError

        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            return Response({"password": exc.detail}, status=400)
        user.set_password(password)
        user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)
