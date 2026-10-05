from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q, Sum
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from apps.contas.mixins import PerfilRequeridoMixin

from .forms import AeronaveForm
from .models import Aeronave


class AeronaveLista(PerfilRequeridoMixin, ListView):
    model = Aeronave
    template_name = "frota/aeronave_lista.html"
    context_object_name = "aeronaves"

    def get_queryset(self):
        return Aeronave.objects.annotate(
            total_voos=Count("viagens", filter=Q(viagens__status="realizada")),
            total_horas=Sum("viagens__horas_voo", filter=Q(viagens__status="realizada")),
        )


class AeronaveCriar(PerfilRequeridoMixin, SuccessMessageMixin, CreateView):
    acao = "gerenciar_aeronaves"
    model = Aeronave
    form_class = AeronaveForm
    template_name = "frota/aeronave_form.html"
    success_url = reverse_lazy("frota:aeronaves")
    success_message = "Aeronave %(prefixo)s cadastrada."


class AeronaveEditar(PerfilRequeridoMixin, SuccessMessageMixin, UpdateView):
    acao = "gerenciar_aeronaves"
    model = Aeronave
    form_class = AeronaveForm
    template_name = "frota/aeronave_form.html"
    success_url = reverse_lazy("frota:aeronaves")
    success_message = "Aeronave %(prefixo)s atualizada."
