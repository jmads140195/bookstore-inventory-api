from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from knox.models import AuthToken
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, Throttled
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserAccess
from .permissions import FullAccess, is_full
from .serializers import (ChangePasswordSerializer, CreateUserSerializer, LoginResponseSerializer,
                          LoginSerializer, ResetPasswordSerializer, UpdateUserSerializer, UserSerializer, check_password)
from .throttles import LoginThrottle

User = get_user_model()


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginThrottle]

    def get_authenticate_header(self, request):
        return "Bearer"

    @extend_schema(request=LoginSerializer, responses=LoginResponseSerializer)
    def post(self, request):
        data = LoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = authenticate(request, **data.validated_data)
        if user is None:
            # Mismo mensaje para inexistente, contraseña incorrecta o inactivo.
            response = Response({"error": {"code": "invalid_credentials", "message": "Credenciales inválidas."}}, status=401)
            response["WWW-Authenticate"] = "Bearer"
            return response
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            if not user.is_active or not user.check_password(data.validated_data["password"]):
                raise AuthenticationFailed("Credenciales inválidas.")
            user.auth_token_set.filter(expiry__lte=timezone.now()).delete()
            if user.auth_token_set.count() >= settings.AUTH_MAX_TOKENS:
                raise Throttled(detail="Límite de sesiones activas. Cierra alguna sesión antes de iniciar otra.")
            token_instance, token = AuthToken.objects.create(user=user)
        response = Response(LoginResponseSerializer({"token": token, "token_type": "Bearer",
                            "expires_at": token_instance.expiry, "user": user}).data)
        response["Cache-Control"] = "no-store"
        return response


class MeView(APIView):
    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        request.auth.delete()
        return Response(status=204)


class LogoutAllView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            user.auth_token_set.all().delete()
        return Response(status=204)


class ChangePasswordView(APIView):
    @extend_schema(request=ChangePasswordSerializer, responses={204: None})
    def post(self, request):
        data = ChangePasswordSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            if not user.check_password(data.validated_data["current_password"]):
                raise serializers.ValidationError({"current_password": ["Contraseña incorrecta."]})
            check_password(data.validated_data["new_password"], user)
            user.set_password(data.validated_data["new_password"])
            user.save(update_fields=["password"])
            user.auth_token_set.all().delete()
        return Response(status=204)


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    permission_classes = [FullAccess]
    lookup_value_regex = "[0-9]+"

    @extend_schema(request=CreateUserSerializer, responses={201: UserSerializer})
    def create(self, request):
        data = CreateUserSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        role = values.pop("role")
        try:
            with transaction.atomic():
                actor = User.objects.select_for_update().get(pk=request.user.pk)
                if not is_full(actor):
                    raise PermissionDenied()
                user = User.objects.create_user(**values)
                UserAccess.objects.create(user=user, role=role)
        except IntegrityError:
            if User.objects.filter(username=values["username"]).exists():
                raise serializers.ValidationError({"username": ["Este nombre de usuario ya existe."]})
            raise
        return Response(UserSerializer(user).data, status=201)

    def locked_target(self, request, pk):
        # Administración poco frecuente: orden único de bloqueo para evitar
        # que dos administradores se desactiven mutuamente en una carrera.
        users = list(User.objects.select_for_update().order_by("pk"))
        actor = next((user for user in users if user.pk == request.user.pk), None)
        if actor is None or not is_full(actor):
            raise PermissionDenied()
        target = get_object_or_404(User, pk=pk)
        if target.pk == actor.pk:
            raise serializers.ValidationError("Usa los endpoints de tu propia cuenta; no puedes cambiar tu rol ni desactivarte.")
        if target.is_superuser:
            raise PermissionDenied("Los superusuarios se administran desde la consola del servidor.")
        return target

    @extend_schema(request=UpdateUserSerializer, responses=UserSerializer)
    def partial_update(self, request, pk=None):
        data = UpdateUserSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            user = self.locked_target(request, pk)
            if "role" in data.validated_data:
                UserAccess.objects.update_or_create(user=user, defaults={"role": data.validated_data["role"]})
            if "is_active" in data.validated_data:
                user.is_active = data.validated_data["is_active"]
                user.save(update_fields=["is_active"])
            user.auth_token_set.all().delete()
        return Response(UserSerializer(user).data)

    @extend_schema(request=ResetPasswordSerializer, responses={204: None})
    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        data = ResetPasswordSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            user = self.locked_target(request, pk)
            check_password(data.validated_data["new_password"], user)
            user.set_password(data.validated_data["new_password"])
            user.save(update_fields=["password"])
            user.auth_token_set.all().delete()
        return Response(status=204)
