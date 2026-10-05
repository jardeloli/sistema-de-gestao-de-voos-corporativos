from .perfis import PERMISSOES, pode


class _Permissoes:
    """Permite usar {% if perms_app.agendar_viagem %} nos templates."""

    def __init__(self, user):
        self._user = user

    def __getattr__(self, acao):
        if acao not in PERMISSOES:
            raise AttributeError(acao)
        return pode(self._user, acao)


def perfis(request):
    return {"perms_app": _Permissoes(request.user)}
