from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView, View

from apps.contas.mixins import PerfilRequeridoMixin
from apps.frota.models import Aeronave

from .forms import (
    AbastecimentoForm, CancelamentoForm, ConclusaoForm, CustoForm, FiltroViagemForm, PassageiroForm, ViagemForm,
)
from .models import Abastecimento, Custo, Passageiro, Status, Viagem


# ---------------------------------------------------------------------------
# Viagens
# ---------------------------------------------------------------------------
class ViagemLista(PerfilRequeridoMixin, ListView):
    """RF10 (histórico), RF11 (agendadas) e RF13 (filtros) em uma única tela com abas."""

    template_name = "viagens/viagem_lista.html"
    context_object_name = "viagens"
    paginate_by = 15
    ABAS = {
        "agendadas": "Agendadas",
        "historico": "Histórico",
        "todas": "Todas",
    }

    def get_aba(self):
        aba = self.request.GET.get("aba", "agendadas")
        return aba if aba in self.ABAS else "agendadas"

    def get_queryset(self):
        qs = Viagem.objects.select_related("aeronave", "responsavel").prefetch_related("passageiros").com_totais()
        aba = self.get_aba()
        hoje = timezone.localdate()
        if aba == "agendadas":
            qs = qs.filter(status=Status.AGENDADA).order_by("data", "horario_previsto")
        elif aba == "historico":
            qs = qs.filter(Q(status__in=[Status.REALIZADA, Status.CANCELADA]) | Q(data__lt=hoje))
        self.filtro = FiltroViagemForm(self.request.GET or None)
        return self.filtro.filtrar(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        params.pop("aba", None)
        ctx.update(
            filtro=self.filtro,
            aba=self.get_aba(),
            abas=self.ABAS,
            querystring=params.urlencode(),
            pendentes=Viagem.objects.filter(status=Status.AGENDADA, data__lt=timezone.localdate()).count(),
        )
        return ctx


class ViagemDetalhe(PerfilRequeridoMixin, DetailView):
    template_name = "viagens/viagem_detalhe.html"
    context_object_name = "viagem"

    def get_queryset(self):
        return Viagem.objects.select_related("aeronave", "responsavel", "cancelada_por").prefetch_related(
            "passageiros", "custos__registrado_por", "abastecimentos"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["custo_form"] = CustoForm()
        ctx["cancelamento_form"] = CancelamentoForm()
        return ctx


class CapacidadesMixin:
    """Envia ao template a capacidade de cada aeronave para o contador de passageiros (JS)."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["capacidades"] = {str(a.pk): a.capacidade_passageiros for a in Aeronave.objects.filter(ativa=True)}
        return ctx


class ViagemCriar(PerfilRequeridoMixin, CapacidadesMixin, SuccessMessageMixin, CreateView):
    """RF03/RF04 – Caso de uso 01 (Agendar viagem)."""

    acao = "agendar_viagem"
    model = Viagem
    form_class = ViagemForm
    template_name = "viagens/viagem_form.html"
    success_message = "Viagem agendada para %(data)s."

    def get_initial(self):
        inicial = super().get_initial()
        if "data" in self.request.GET:
            inicial["data"] = self.request.GET["data"]
        return inicial

    def form_valid(self, form):
        form.instance.responsavel = self.request.user
        return super().form_valid(form)

    def get_success_message(self, cleaned_data):
        return f"Viagem agendada para {cleaned_data['data']:%d/%m/%Y}."

    def get_success_url(self):
        return reverse("viagens:detalhe", args=[self.object.pk])


class ViagemEditar(PerfilRequeridoMixin, CapacidadesMixin, SuccessMessageMixin, UpdateView):
    """RF05 – Alteração de viagens (apenas enquanto agendada)."""

    acao = "agendar_viagem"
    model = Viagem
    form_class = ViagemForm
    template_name = "viagens/viagem_form.html"
    success_message = "Alterações salvas."

    def dispatch(self, request, *args, **kwargs):
        viagem = get_object_or_404(Viagem, pk=kwargs["pk"])
        if request.user.is_authenticated and not viagem.pode_alterar:
            messages.warning(request, "Viagens realizadas ou canceladas não podem ser alteradas.")
            return redirect("viagens:detalhe", pk=viagem.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("viagens:detalhe", args=[self.object.pk])


class ViagemCancelar(PerfilRequeridoMixin, FormView):
    """RF06 – Cancela mantendo o registro no histórico."""

    acao = "agendar_viagem"
    form_class = CancelamentoForm
    template_name = "viagens/viagem_cancelar.html"
    http_method_names = ["get", "post"]

    def dispatch(self, request, *args, **kwargs):
        self.viagem = get_object_or_404(Viagem, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(viagem=self.viagem, **kwargs)

    def form_valid(self, form):
        if not self.viagem.pode_cancelar:
            messages.warning(self.request, "Esta viagem não está mais agendada.")
        else:
            self.viagem.cancelar(self.request.user, form.cleaned_data["motivo"])
            messages.success(self.request, "Viagem cancelada. O registro continua disponível no histórico.")
        return redirect("viagens:detalhe", pk=self.viagem.pk)


class ViagemConcluir(PerfilRequeridoMixin, UpdateView):
    """Fluxo, etapa 3 – registra horas de voo e consumo após a viagem."""

    acao = "concluir_viagem"
    model = Viagem
    form_class = ConclusaoForm
    template_name = "viagens/viagem_concluir.html"

    def dispatch(self, request, *args, **kwargs):
        viagem = get_object_or_404(Viagem, pk=kwargs["pk"])
        if request.user.is_authenticated and not viagem.pode_concluir:
            messages.warning(request, "Só é possível registrar a realização de viagens agendadas a partir do dia do voo.")
            return redirect("viagens:detalhe", pk=viagem.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.status = Status.REALIZADA
        resposta = super().form_valid(form)
        messages.success(self.request, "Voo registrado como realizado. Lance agora os abastecimentos e custos.")
        return resposta

    def get_success_url(self):
        return reverse("viagens:detalhe", args=[self.object.pk])


# ---------------------------------------------------------------------------
# Custos (RF07 – Caso de uso 02)
# ---------------------------------------------------------------------------
class CustoCriar(PerfilRequeridoMixin, CreateView):
    acao = "registrar_custo"
    model = Custo
    form_class = CustoForm
    template_name = "viagens/custo_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.viagem = get_object_or_404(Viagem, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(viagem=self.viagem, **kwargs)

    def form_valid(self, form):
        if self.viagem.status == Status.CANCELADA:
            messages.error(self.request, "Não é possível lançar custos em uma viagem cancelada.")
            return redirect("viagens:detalhe", pk=self.viagem.pk)
        form.instance.viagem = self.viagem
        form.instance.registrado_por = self.request.user
        form.save()
        messages.success(self.request, f"Custo de R$ {form.instance.valor:.2f} registrado.".replace(".", ","))
        return HttpResponseRedirect(reverse("viagens:detalhe", args=[self.viagem.pk]) + "#custos")


class CustoExcluir(PerfilRequeridoMixin, View):
    acao = "registrar_custo"
    http_method_names = ["post"]

    def post(self, request, pk):
        custo = get_object_or_404(Custo, pk=pk)
        viagem_id = custo.viagem_id
        custo.delete()
        messages.success(request, "Custo removido.")
        return HttpResponseRedirect(reverse("viagens:detalhe", args=[viagem_id]) + "#custos")


# ---------------------------------------------------------------------------
# Abastecimentos (RF08/RF09 – Caso de uso 03)
# ---------------------------------------------------------------------------
class AbastecimentoLista(PerfilRequeridoMixin, ListView):
    template_name = "viagens/abastecimento_lista.html"
    context_object_name = "abastecimentos"
    paginate_by = 20

    def get_queryset(self):
        return Abastecimento.objects.select_related("aeronave", "viagem", "registrado_por")


class AbastecimentoCriar(PerfilRequeridoMixin, SuccessMessageMixin, CreateView):
    acao = "registrar_abastecimento"
    model = Abastecimento
    form_class = AbastecimentoForm
    template_name = "viagens/abastecimento_form.html"
    success_message = "Abastecimento registrado."

    def get_initial(self):
        inicial = super().get_initial()
        viagem_id = self.request.GET.get("viagem")
        if viagem_id and viagem_id.isdigit():
            viagem = Viagem.objects.filter(pk=viagem_id).first()
            if viagem:
                inicial.update(viagem=viagem, aeronave=viagem.aeronave, data=viagem.data)
        return inicial

    def form_valid(self, form):
        form.instance.registrado_por = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.viagem_id:
            return reverse("viagens:detalhe", args=[self.object.viagem_id]) + "#combustivel"
        return reverse("viagens:abastecimentos")


class AbastecimentoEditar(PerfilRequeridoMixin, SuccessMessageMixin, UpdateView):
    acao = "registrar_abastecimento"
    model = Abastecimento
    form_class = AbastecimentoForm
    template_name = "viagens/abastecimento_form.html"
    success_message = "Abastecimento atualizado."
    success_url = reverse_lazy("viagens:abastecimentos")


# ---------------------------------------------------------------------------
# Passageiros
# ---------------------------------------------------------------------------
class PassageiroLista(PerfilRequeridoMixin, ListView):
    template_name = "viagens/passageiro_lista.html"
    context_object_name = "passageiros"
    paginate_by = 25

    def get_queryset(self):
        qs = Passageiro.objects.annotate(total_viagens=Count("viagens", filter=Q(viagens__status=Status.REALIZADA)))
        busca = self.request.GET.get("q", "").strip()
        if busca:
            qs = qs.filter(Q(nome__icontains=busca) | Q(setor__icontains=busca))
        return qs.order_by("-ativo", "nome")


class PassageiroCriar(PerfilRequeridoMixin, SuccessMessageMixin, CreateView):
    acao = "gerenciar_passageiros"
    model = Passageiro
    form_class = PassageiroForm
    template_name = "viagens/passageiro_form.html"
    success_url = reverse_lazy("viagens:passageiros")
    success_message = "Passageiro %(nome)s cadastrado."


class PassageiroEditar(PerfilRequeridoMixin, SuccessMessageMixin, UpdateView):
    acao = "gerenciar_passageiros"
    model = Passageiro
    form_class = PassageiroForm
    template_name = "viagens/passageiro_form.html"
    success_url = reverse_lazy("viagens:passageiros")
    success_message = "Passageiro %(nome)s atualizado."
