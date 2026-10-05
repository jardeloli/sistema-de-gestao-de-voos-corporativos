from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .perfis import pode


class PerfilRequeridoMixin(LoginRequiredMixin):
    """Exige login e, se `acao` estiver definida, a permissão correspondente."""

    acao = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.acao and not pode(request.user, self.acao):
            raise PermissionDenied("Seu perfil não tem acesso a esta funcionalidade.")
        return super().dispatch(request, *args, **kwargs)
