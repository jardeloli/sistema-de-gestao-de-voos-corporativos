"""
Perfis de acesso (RNF02 – Controle de acesso).

Cada perfil corresponde a um Group do Django. Superusuários têm acesso a tudo.
As constantes abaixo são a única fonte de verdade sobre "quem pode o quê":
views, templates e testes consultam este módulo.
"""
ADMINISTRADOR = "Administrador"
GESTOR = "Gestor"
AGENDADOR = "Agendador"
OPERACIONAL = "Operacional"

TODOS = (ADMINISTRADOR, GESTOR, AGENDADOR, OPERACIONAL)

DESCRICOES = {
    ADMINISTRADOR: "Acesso total, incluindo usuários e aeronaves.",
    GESTOR: "Painel gerencial, custos e acompanhamento das viagens.",
    AGENDADOR: "Agenda, altera e cancela viagens; cadastra passageiros.",
    OPERACIONAL: "Registra voos realizados, horas de voo e abastecimentos.",
}

# Ação -> perfis autorizados
PERMISSOES = {
    "gerenciar_usuarios": {ADMINISTRADOR},
    "gerenciar_aeronaves": {ADMINISTRADOR},
    "gerenciar_passageiros": {ADMINISTRADOR, AGENDADOR},
    "agendar_viagem": {ADMINISTRADOR, GESTOR, AGENDADOR},
    "concluir_viagem": {ADMINISTRADOR, OPERACIONAL},
    "registrar_custo": {ADMINISTRADOR, GESTOR, OPERACIONAL},
    "registrar_abastecimento": {ADMINISTRADOR, OPERACIONAL},
    "ver_painel": {ADMINISTRADOR, GESTOR},
}


def perfis_do_usuario(user):
    if not user.is_authenticated:
        return set()
    cache = getattr(user, "_perfis_cache", None)
    if cache is None:
        cache = set(user.groups.values_list("name", flat=True))
        user._perfis_cache = cache
    return cache


def pode(user, acao):
    """Retorna True se o usuário pode executar a ação informada."""
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return bool(perfis_do_usuario(user) & PERMISSOES[acao])
