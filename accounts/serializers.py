from collections.abc import Mapping

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import UserAccess
from .permissions import role_for

User = get_user_model()


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({key: ["Campo no permitido."] for key in sorted(unknown)})
        return super().to_internal_value(data)


def check_password(password, user):
    try:
        password_validation.validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": exc.messages}) from exc


class LoginSerializer(StrictSerializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "is_active", "date_joined"]

    def get_role(self, obj) -> str:
        return role_for(obj)


class CreateUserSerializer(StrictSerializer):
    username = serializers.CharField(max_length=150, validators=[
        *User._meta.get_field("username").validators,
        UniqueValidator(User.objects.all(), lookup="iexact", message="Este nombre de usuario ya existe."),
    ])
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    role = serializers.ChoiceField(choices=UserAccess.Role.choices, default=UserAccess.Role.BASIC)

    def validate(self, attrs):
        user = User(**{key: attrs[key] for key in ["username", "email", "first_name", "last_name"]})
        check_password(attrs["password"], user)
        return attrs


class UpdateUserSerializer(StrictSerializer):
    role = serializers.ChoiceField(choices=UserAccess.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Indica role o is_active.")
        return attrs


class ChangePasswordSerializer(StrictSerializer):
    current_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


class ResetPasswordSerializer(StrictSerializer):
    new_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    token_type = serializers.CharField()
    expires_at = serializers.DateTimeField()
    user = UserSerializer()
