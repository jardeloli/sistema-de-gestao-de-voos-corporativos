from datetime import datetime, timedelta

from django import forms
from django.db.models import Q
from django.utils import timezone

from apps.core_forms import EstiloBootstrapMixin
from apps.frota.models import Aeronave

from .models import Abastecimento, Custo, Finalidade, Passageiro, Status, Viagem

JANELA_CONFLITO = timedelta(hours=2)


class ViagemForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Viagem
        fields = [
            "aeronave", "data", "horario_previsto", "origem", "destino",
            "passageiros", "finalidade", "descricao", "observacoes",
        ]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "horario_previsto": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "passageiros": forms.CheckboxSelectMultiple,
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["aeronave"].queryset = Aeronave.objects.filter(ativa=True)
        self.fields["aeronave"].empty_label = "Selecione a aeronave"
        filtro = Q(ativo=True)
        if self.instance.pk:  # mantém passageiros já vinculados, mesmo se inativados depois
            filtro |= Q(pk__in=self.instance.passageiros.values("pk"))
        self.fields["passageiros"].queryset = Passageiro.objects.filter(filtro)
        self.fields["passageiros"].help_text = "Marque quem vai embarcar."
        self.fields["finalidade"].choices = [("", "Selecione a finalidade")] + list(Finalidade.choices)
        # RF03: descrição/finalidade obrigatórias (reforço explícito)
        self.fields["descricao"].required = True
        self.fields["finalidade"].required = True
        if not self.instance.pk:
            self.fields["data"].widget.attrs["min"] = timezone.localdate().isoformat()

    def clean_data(self):
        data = self.cleaned_data["data"]
        if not self.instance.pk and data < timezone.localdate():
            raise forms.ValidationError("Não é possível agendar uma viagem em data passada.")
        return data

    def clean_descricao(self):
        descricao = (self.cleaned_data.get("descricao") or "").strip()
        if len(descricao) < 10:
            raise forms.ValidationError("Descreva o motivo da viagem com pelo menos 10 caracteres.")
        return descricao

    def clean(self):
        dados = super().clean()
        origem, destino = dados.get("origem"), dados.get("destino")
        if origem and destino and origem.strip().lower() == destino.strip().lower():
            self.add_error("destino", "O destino precisa ser diferente da origem.")

        aeronave, passageiros = dados.get("aeronave"), dados.get("passageiros")
        if aeronave and passageiros is not None:
            if len(passageiros) > aeronave.capacidade_passageiros:
                self.add_error(
                    "passageiros",
                    f"A aeronave {aeronave.prefixo} comporta {aeronave.capacidade_passageiros} passageiros; "
                    f"foram marcados {len(passageiros)}.",
                )

        # Consultar disponibilidade: evita dois voos da mesma aeronave muito próximos
        data, hora = dados.get("data"), dados.get("horario_previsto")
        if aeronave and data and hora:
            inicio = datetime.combine(data, hora)
            conflitos = (
                Viagem.objects.filter(aeronave=aeronave, data=data, status=Status.AGENDADA)
                .exclude(pk=self.instance.pk)
            )
            for outra in conflitos:
                if abs(datetime.combine(data, outra.horario_previsto) - inicio) < JANELA_CONFLITO:
                    self.add_error(
                        "horario_previsto",
                        f"A aeronave já tem voo agendado às {outra.horario_previsto:%H:%M} nesse dia "
                        f"({outra.origem} → {outra.destino}). Escolha um horário com pelo menos 2 h de diferença.",
                    )
                    break
        return dados


class CancelamentoForm(EstiloBootstrapMixin, forms.Form):
    motivo = forms.CharField(
        label="Motivo do cancelamento",
        max_length=200,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Fica registrado no histórico da viagem.",
    )


class ConclusaoForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Viagem
        fields = ["horas_voo", "combustivel_consumido", "observacoes"]
        widgets = {
            "horas_voo": forms.NumberInput(attrs={"step": "0.1", "min": "0.1", "inputmode": "decimal"}),
            "combustivel_consumido": forms.NumberInput(attrs={"step": "0.1", "min": "0.1", "inputmode": "decimal"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["horas_voo"].required = True
        self.fields["combustivel_consumido"].required = True


class CustoForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Custo
        fields = ["tipo", "valor", "descricao", "data"]
        widgets = {
            "valor": forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "inputmode": "decimal"}),
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].help_text = "Combustível é lançado em Abastecimentos e entra no total automaticamente."


class AbastecimentoForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Abastecimento
        fields = ["aeronave", "viagem", "data", "quantidade_litros", "tipo_combustivel", "valor_litro", "local"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "quantidade_litros": forms.NumberInput(attrs={"step": "0.1", "min": "0.1", "inputmode": "decimal"}),
            "valor_litro": forms.NumberInput(attrs={"step": "0.001", "min": "0.001", "inputmode": "decimal"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["aeronave"].queryset = Aeronave.objects.filter(ativa=True)
        self.fields["aeronave"].empty_label = "Selecione a aeronave"
        self.fields["viagem"].queryset = (
            Viagem.objects.exclude(status=Status.CANCELADA).select_related("aeronave").order_by("-data")[:60]
        )
        self.fields["viagem"].empty_label = "Sem viagem vinculada"
        self.fields["viagem"].label_from_instance = (
            lambda v: f"{v.data:%d/%m} · {v.aeronave.prefixo} · {v.origem} → {v.destino}"
        )

    def clean(self):
        dados = super().clean()
        viagem, aeronave = dados.get("viagem"), dados.get("aeronave")
        if viagem and aeronave and viagem.aeronave_id != aeronave.pk:
            self.add_error("viagem", f"Essa viagem foi feita com a aeronave {viagem.aeronave.prefixo}.")
        return dados


class PassageiroForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Passageiro
        fields = ["nome", "setor", "email", "ativo"]


class FiltroViagemForm(EstiloBootstrapMixin, forms.Form):
    """RF13 – filtros por período, origem, destino, finalidade, situação e passageiro."""

    inicio = forms.DateField(label="De", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    fim = forms.DateField(label="Até", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    origem = forms.CharField(label="Origem", required=False)
    destino = forms.CharField(label="Destino", required=False)
    finalidade = forms.ChoiceField(label="Finalidade", required=False, choices=[("", "Todas")] + list(Finalidade.choices))
    status = forms.ChoiceField(label="Situação", required=False, choices=[("", "Todas")] + list(Status.choices))
    passageiro = forms.ModelChoiceField(
        label="Passageiro", required=False, queryset=Passageiro.objects.all(), empty_label="Todos"
    )

    def filtrar(self, qs):
        if not self.is_valid():
            return qs
        d = self.cleaned_data
        if d.get("inicio"):
            qs = qs.filter(data__gte=d["inicio"])
        if d.get("fim"):
            qs = qs.filter(data__lte=d["fim"])
        if d.get("origem"):
            qs = qs.filter(origem__icontains=d["origem"])
        if d.get("destino"):
            qs = qs.filter(destino__icontains=d["destino"])
        if d.get("finalidade"):
            qs = qs.filter(finalidade=d["finalidade"])
        if d.get("status"):
            qs = qs.filter(status=d["status"])
        if d.get("passageiro"):
            qs = qs.filter(passageiros=d["passageiro"])
        return qs

    @property
    def ativos(self):
        """Quantidade de filtros preenchidos (exibida no botão em telas pequenas)."""
        if not self.is_bound or not self.is_valid():
            return 0
        return sum(1 for v in self.cleaned_data.values() if v)
