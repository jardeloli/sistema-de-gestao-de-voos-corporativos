from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import DecimalField, OuterRef, Subquery, Sum
from django.utils import timezone


class Passageiro(models.Model):
    nome = models.CharField("Nome completo", max_length=120)
    setor = models.CharField("Setor / cargo", max_length=80, blank=True, help_text="Ex.: Diretoria comercial")
    email = models.EmailField("E-mail", blank=True)
    ativo = models.BooleanField("Ativo", default=True, help_text="Inativos não aparecem em novos agendamentos.")

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.setor})" if self.setor else self.nome


class Finalidade(models.TextChoices):
    VISITA_FILIAL = "visita_filial", "Visita a filial"
    REUNIAO_CLIENTE = "reuniao_cliente", "Reunião com cliente"
    TREINAMENTO = "treinamento", "Treinamento de colaboradores"
    EVENTO = "evento", "Participação em evento"
    VISITA_TECNICA = "visita_tecnica", "Visita técnica"
    ACOMPANHAMENTO = "acompanhamento", "Acompanhamento de operação"
    REUNIAO_ADM = "reuniao_adm", "Reunião administrativa"
    OUTRA = "outra", "Outra (detalhar na descrição)"


class Status(models.TextChoices):
    AGENDADA = "agendada", "Agendada"
    REALIZADA = "realizada", "Realizada"
    CANCELADA = "cancelada", "Cancelada"


class ViagemQuerySet(models.QuerySet):
    def ativas(self):
        return self.exclude(status=Status.CANCELADA)

    def proximas(self):
        return self.filter(status=Status.AGENDADA, data__gte=timezone.localdate()).order_by("data", "horario_previsto")

    def com_totais(self):
        """Anota despesas e combustível por viagem.

        Usa subconsultas em vez de dois Sum() com JOIN, que multiplicariam
        os valores quando a viagem tem vários custos e vários abastecimentos.
        """
        def soma(modelo, campo):
            return Subquery(
                modelo.objects.filter(viagem=OuterRef("pk")).values("viagem").annotate(t=Sum(campo)).values("t"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )

        return self.annotate(_despesas=soma(Custo, "valor"), _combustivel=soma(Abastecimento, "valor_total"))


class Viagem(models.Model):
    """RF03 a RF06 – cadastro, agendamento, alteração e cancelamento de viagens."""

    aeronave = models.ForeignKey("frota.Aeronave", on_delete=models.PROTECT, related_name="viagens")
    data = models.DateField("Data da viagem")
    horario_previsto = models.TimeField("Horário previsto")
    origem = models.CharField("Origem", max_length=80, help_text="Cidade/UF ou aeródromo. Ex.: Balsas – MA (SNBS)")
    destino = models.CharField("Destino", max_length=80, help_text="Cidade/UF ou aeródromo. Ex.: Palmas – TO (SBPJ)")
    passageiros = models.ManyToManyField(Passageiro, related_name="viagens", verbose_name="Passageiros")
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="agendamentos",
        verbose_name="Responsável pelo agendamento",
    )
    finalidade = models.CharField("Finalidade do voo", max_length=30, choices=Finalidade.choices)
    descricao = models.TextField(
        "Descrição da viagem",
        help_text="Explique o motivo do deslocamento. Ex.: Reunião de fechamento de safra com o cliente X.",
    )
    observacoes = models.TextField("Observações", blank=True)

    status = models.CharField("Situação", max_length=10, choices=Status.choices, default=Status.AGENDADA)

    # Preenchidos após a realização do voo (fluxo, etapa 3)
    horas_voo = models.DecimalField(
        "Horas de voo", max_digits=5, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.1"))], help_text="Em horas decimais. Ex.: 1,5 = 1h30",
    )
    combustivel_consumido = models.DecimalField(
        "Combustível consumido (L)", max_digits=8, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.1"))],
    )

    # Cancelamento (RF06) – o registro é mantido para histórico
    motivo_cancelamento = models.CharField("Motivo do cancelamento", max_length=200, blank=True)
    cancelada_em = models.DateTimeField(null=True, blank=True)
    cancelada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = ViagemQuerySet.as_manager()

    class Meta:
        ordering = ["-data", "-horario_previsto"]
        verbose_name = "viagem"
        verbose_name_plural = "viagens"
        indexes = [models.Index(fields=["status", "data"])]

    def __str__(self):
        return f"{self.origem} → {self.destino} em {self.data:%d/%m/%Y}"

    # --- Regras de estado -------------------------------------------------
    @property
    def pode_alterar(self):
        return self.status == Status.AGENDADA

    @property
    def pode_cancelar(self):
        return self.status == Status.AGENDADA

    @property
    def pode_concluir(self):
        return self.status == Status.AGENDADA and self.data <= timezone.localdate()

    @property
    def aguardando_registro(self):
        """Voo agendado cuja data já passou e ainda não foi registrado como realizado."""
        return self.status == Status.AGENDADA and self.data < timezone.localdate()

    def cancelar(self, usuario, motivo):
        if not self.pode_cancelar:
            raise ValidationError("Somente viagens agendadas podem ser canceladas.")
        self.status = Status.CANCELADA
        self.motivo_cancelamento = motivo
        self.cancelada_em = timezone.now()
        self.cancelada_por = usuario
        self.save(update_fields=["status", "motivo_cancelamento", "cancelada_em", "cancelada_por", "atualizado_em"])

    # --- Totais -----------------------------------------------------------
    @property
    def custo_despesas(self):
        valor = getattr(self, "_despesas", None)
        if valor is None:
            valor = self.custos.aggregate(t=Sum("valor"))["t"]
        return valor or Decimal("0")

    @property
    def custo_combustivel(self):
        valor = getattr(self, "_combustivel", None)
        if valor is None:
            valor = self.abastecimentos.aggregate(t=Sum("valor_total"))["t"]
        return valor or Decimal("0")

    @property
    def custo_total(self):
        return self.custo_despesas + self.custo_combustivel

    @property
    def consumo_por_hora(self):
        if self.horas_voo and self.combustivel_consumido:
            return (self.combustivel_consumido / self.horas_voo).quantize(Decimal("0.1"))
        return None


class TipoCusto(models.TextChoices):
    # Combustível não aparece aqui de propósito: ele é lançado em Abastecimentos
    # e somado automaticamente ao custo da viagem (evita contagem em dobro).
    TAXAS = "taxas", "Taxas aeroportuárias"
    ALIMENTACAO = "alimentacao", "Alimentação"
    HOSPEDAGEM = "hospedagem", "Hospedagem"
    MANUTENCAO = "manutencao", "Manutenção relacionada ao voo"
    OUTROS = "outros", "Outros custos"


class Custo(models.Model):
    """RF07 – Controle de custos."""

    viagem = models.ForeignKey(Viagem, on_delete=models.CASCADE, related_name="custos")
    tipo = models.CharField("Tipo de custo", max_length=20, choices=TipoCusto.choices)
    valor = models.DecimalField("Valor (R$)", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    descricao = models.CharField("Descrição", max_length=200, help_text="Ex.: Taxa de pouso em Palmas")
    data = models.DateField("Data da despesa", default=timezone.localdate)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data", "-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} – R$ {self.valor}"


class TipoCombustivel(models.TextChoices):
    QAV = "qav1", "QAV-1 (querosene de aviação)"
    AVGAS = "avgas", "AVGAS 100LL (gasolina de aviação)"


class Abastecimento(models.Model):
    """RF08 – Controle de abastecimento."""

    aeronave = models.ForeignKey("frota.Aeronave", on_delete=models.PROTECT, related_name="abastecimentos")
    viagem = models.ForeignKey(
        Viagem, on_delete=models.SET_NULL, null=True, blank=True, related_name="abastecimentos",
        verbose_name="Viagem relacionada", help_text="Opcional. Deixe em branco para abastecimentos fora de viagem.",
    )
    data = models.DateField("Data", default=timezone.localdate)
    quantidade_litros = models.DecimalField(
        "Quantidade abastecida (L)", max_digits=8, decimal_places=1, validators=[MinValueValidator(Decimal("0.1"))]
    )
    tipo_combustivel = models.CharField("Tipo de combustível", max_length=10, choices=TipoCombustivel.choices)
    valor_litro = models.DecimalField(
        "Valor por litro (R$)", max_digits=8, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))]
    )
    valor_total = models.DecimalField("Valor total (R$)", max_digits=12, decimal_places=2, editable=False)
    local = models.CharField("Local do abastecimento", max_length=80, help_text="Ex.: Aeroporto de Balsas (SNBS)")
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data", "-criado_em"]

    def __str__(self):
        return f"{self.quantidade_litros} L em {self.local} ({self.data:%d/%m/%Y})"

    def clean(self):
        if self.viagem_id and self.aeronave_id and self.viagem.aeronave_id != self.aeronave_id:
            raise ValidationError({"viagem": "A viagem selecionada é de outra aeronave."})

    def save(self, *args, **kwargs):
        # Caso de uso 03: o sistema calcula o valor total
        self.valor_total = (self.quantidade_litros * self.valor_litro).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
