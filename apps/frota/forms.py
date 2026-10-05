from django import forms

from apps.core_forms import EstiloBootstrapMixin

from .models import Aeronave


class AeronaveForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Aeronave
        fields = ["identificacao", "fabricante", "modelo", "prefixo", "capacidade_passageiros", "ativa"]
        widgets = {"prefixo": forms.TextInput(attrs={"style": "text-transform:uppercase", "maxlength": 6})}

    def clean_prefixo(self):
        return self.cleaned_data["prefixo"].upper().strip()
