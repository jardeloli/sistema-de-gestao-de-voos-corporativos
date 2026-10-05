from datetime import date
from decimal import Decimal

from django import forms
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.views.generic import TemplateView

from apps.contas.mixins import PerfilRequeridoMixin
from apps.core_forms import EstiloBootstrapMixin
from apps.viagens.models import Abastecimento, Custo, Finalidade, Status, Viagem

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _primeiro_dia_meses_atras(base, meses):
    ano, mes = base.year, base.month - meses
    while mes <= 0:
        mes += 12
        ano -= 1
    return date(ano, mes, 1)


class Inicio(PerfilRequeridoMixin, TemplateView):
    """Tela inicial: próximos voos (RF11) e pendências do usuário."""

    template_name = "painel/inicio.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoje = timezone.localdate()
        base = Viagem.objects.select_related("aeronave").prefetch_related("passageiros")
        ctx["proximas"] = base.proximas()[:6]
        ctx["pendentes"] = base.filter(status=Status.AGENDADA, data__lt=hoje).order_by("data")[:5]
        ctx["hoje"] = hoje
        mes_inicio = hoje.replace(day=1)
        realizadas_mes = Viagem.objects.filter(status=Status.REALIZADA, data__gte=mes_inicio, data__lte=hoje)
        ctx["mes"] = {
            "voos": realizadas_mes.count(),
            "horas": realizadas_mes.aggregate(t=Sum("horas_voo"))["t"] or 0,
            "agendadas": Viagem.objects.filter(status=Status.AGENDADA, data__gte=hoje).count(),
        }
        return ctx


class PeriodoForm(EstiloBootstrapMixin, forms.Form):
    inicio = forms.DateField(label="De", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    fim = forms.DateField(label="Até", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))

    def clean(self):
        d = super().clean()
        if d.get("inicio") and d.get("fim") and d["inicio"] > d["fim"]:
            raise forms.ValidationError("A data inicial deve ser anterior à final.")
        return d


class Dashboard(PerfilRequeridoMixin, TemplateView):
    """RF12 – Dashboard gerencial (Caso de uso 04)."""

    acao = "ver_painel"
    template_name = "painel/dashboard.html"

    def periodo(self):
        hoje = timezone.localdate()
        padrao = {"inicio": _primeiro_dia_meses_atras(hoje, 11), "fim": hoje}
        form = PeriodoForm(self.request.GET or None, initial=padrao)
        if form.is_bound and form.is_valid():
            return form, form.cleaned_data["inicio"], form.cleaned_data["fim"]
        if not form.is_bound:
            form = PeriodoForm(initial=padrao)
        return form, padrao["inicio"], padrao["fim"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form, inicio, fim = self.periodo()
        hoje = timezone.localdate()

        realizadas = Viagem.objects.filter(status=Status.REALIZADA, data__range=(inicio, fim))
        totais = realizadas.aggregate(horas=Sum("horas_voo"), consumo=Sum("combustivel_consumido"))
        qtd = realizadas.count()
        horas = totais["horas"] or Decimal("0")
        consumo = totais["consumo"] or Decimal("0")
        despesas = Custo.objects.filter(viagem__in=realizadas).aggregate(t=Sum("valor"))["t"] or Decimal("0")
        combustivel = (
            Abastecimento.objects.filter(viagem__in=realizadas).aggregate(t=Sum("valor_total"))["t"] or Decimal("0")
        )
        custo_total = despesas + combustivel

        # Série mensal (quantidade de viagens por período)
        por_mes = {
            (r["mes"].year, r["mes"].month): r
            for r in realizadas.annotate(mes=TruncMonth("data")).values("mes").annotate(
                voos=Count("id"), horas=Sum("horas_voo")
            )
        }
        rotulos, serie_voos, serie_horas = [], [], []
        cursor = date(inicio.year, inicio.month, 1)
        while cursor <= fim:
            r = por_mes.get((cursor.year, cursor.month), {})
            rotulos.append(f"{MESES[cursor.month - 1]}/{cursor:%y}")
            serie_voos.append(r.get("voos", 0))
            serie_horas.append(float(r.get("horas") or 0))
            cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)

        finalidades = dict(Finalidade.choices)
        top_finalidades = [
            {"nome": finalidades[r["finalidade"]], "total": r["total"]}
            for r in realizadas.values("finalidade").annotate(total=Count("id")).order_by("-total")[:6]
        ]
        top_destinos = list(realizadas.values("destino").annotate(total=Count("id")).order_by("-total", "destino")[:5])

        custos_por_tipo = [
            {"nome": "Combustível", "total": float(combustivel)},
        ] + [
            {"nome": dict(Custo._meta.get_field("tipo").choices)[r["tipo"]], "total": float(r["total"])}
            for r in Custo.objects.filter(viagem__in=realizadas).values("tipo").annotate(total=Sum("valor")).order_by("-total")
        ]

        ctx.update(
            form=form,
            inicio=inicio,
            fim=fim,
            atalhos=[
                ("Este mês", hoje.replace(day=1), hoje),
                ("Últimos 3 meses", _primeiro_dia_meses_atras(hoje, 2), hoje),
                ("Este ano", date(hoje.year, 1, 1), hoje),
                ("Últimos 12 meses", _primeiro_dia_meses_atras(hoje, 11), hoje),
            ],
            kpi={
                "viagens": qtd,
                "horas": horas,
                "consumo": consumo,
                "consumo_hora": (consumo / horas).quantize(Decimal("0.1")) if horas else None,
                "custo_total": custo_total,
                "custo_medio": (custo_total / qtd).quantize(Decimal("0.01")) if qtd else None,
                "custo_hora": (custo_total / horas).quantize(Decimal("0.01")) if horas else None,
                "canceladas": Viagem.objects.filter(status=Status.CANCELADA, data__range=(inicio, fim)).count(),
            },
            linhas_mes=list(zip(rotulos, serie_voos, serie_horas)),
            top_destinos=top_destinos,
            top_finalidades=top_finalidades,
            graficos={
                "meses": rotulos,
                "voos": serie_voos,
                "horas": serie_horas,
                "custos": custos_por_tipo,
            },
        )
        return ctx
