from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

validar_prefixo = RegexValidator(
    r"^[A-Z]{2}-[A-Z]{3}$",
    "Use o formato de matrícula brasileira: duas letras, hífen e três letras (ex.: PR-LVN).",
)


class Aeronave(models.Model):
    """RF02 – Cadastro de aeronave."""

    identificacao = models.CharField(
        "Identificação", max_length=60, help_text="Nome usado internamente. Ex.: King Air da diretoria."
    )
    fabricante = models.CharField("Fabricante", max_length=60, blank=True)
    modelo = models.CharField("Modelo", max_length=60)
    prefixo = models.CharField(
        "Prefixo (matrícula)", max_length=6, unique=True, validators=[validar_prefixo],
        help_text="Ex.: PR-LVN",
    )
    capacidade_passageiros = models.PositiveSmallIntegerField(
        "Capacidade de passageiros", validators=[MinValueValidator(1)]
    )
    ativa = models.BooleanField("Em operação", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-ativa", "prefixo"]
        verbose_name = "aeronave"
        verbose_name_plural = "aeronaves"

    def __str__(self):
        return f"{self.prefixo} ({self.modelo})"

    def save(self, *args, **kwargs):
        self.prefixo = (self.prefixo or "").upper().strip()
        super().save(*args, **kwargs)
