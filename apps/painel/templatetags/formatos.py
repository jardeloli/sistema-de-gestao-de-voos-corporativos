from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _br(valor, casas):
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


@register.filter
def moeda(valor):
    """1234.5 -> 'R$ 1.234,50'"""
    try:
        return f"R$\u00a0{_br(Decimal(valor or 0), 2)}"  # espaço não separável
    except (InvalidOperation, TypeError, ValueError):
        return "—"


@register.filter
def numero(valor, casas=1):
    try:
        return _br(Decimal(valor), int(casas))
    except (InvalidOperation, TypeError, ValueError):
        return "—"


@register.filter
def horas(valor):
    """1.5 -> '1h30'"""
    if valor in (None, ""):
        return "—"
    total_min = int(round(Decimal(valor) * 60))
    h, m = divmod(total_min, 60)
    return f"{h}h{m:02d}"


@register.simple_tag(takes_context=True)
def nav_ativo(context, *prefixos):
    """Retorna 'page' para usar em aria-current quando a URL atual começa com um dos prefixos."""
    caminho = context["request"].path
    for p in prefixos:
        if (p == "/" and caminho == "/") or (p != "/" and caminho.startswith(p)):
            return "page"
    return ""
