from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import UserAccess


def role_for(user):
    if user.is_superuser:
        return UserAccess.Role.FULL
    # Consultar el rol actual; nunca confiar en un rol enviado en el token.
    return UserAccess.objects.filter(user=user).values_list("role", flat=True).first() or UserAccess.Role.BASIC


def is_full(user):
    return user.is_authenticated and user.is_active and role_for(user) == UserAccess.Role.FULL


class FullAccess(BasePermission):
    message = "Esta operación requiere acceso completo."

    def has_permission(self, request, view):
        return is_full(request.user)


class InventoryAccess(BasePermission):
    message = "El acceso básico permite únicamente consultar el inventario."

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_active and
                    (request.method in SAFE_METHODS or is_full(request.user)))
