from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password

from apps.core_forms import EstiloBootstrapMixin

from .perfis import DESCRICOES, TODOS


class LoginForm(EstiloBootstrapMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuário"
        self.fields["username"].widget.attrs.update({"autocomplete": "username", "autofocus": True})
        self.fields["password"].widget.attrs.update({"autocomplete": "current-password"})


class TrocaSenhaForm(EstiloBootstrapMixin, PasswordChangeForm):
    pass


class UsuarioForm(EstiloBootstrapMixin, forms.ModelForm):
    perfil = forms.ModelChoiceField(
        queryset=Group.objects.filter(name__in=TODOS).order_by("name"),
        label="Perfil de acesso",
        help_text="Define o que o usuário pode fazer no sistema.",
    )
    senha = forms.CharField(
        label="Senha",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Obrigatória no cadastro. Na edição, preencha apenas para redefinir.",
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "is_active"]
        labels = {
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "username": "Usuário (login)",
            "email": "E-mail",
            "is_active": "Usuário ativo",
        }
        help_texts = {
            "username": "Sem espaços. Ex.: carlos.silva",
            "is_active": "Desmarque para bloquear o acesso sem apagar o histórico.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["perfil"].label_from_instance = lambda g: f"{g.name} — {DESCRICOES.get(g.name, '')}"
        if self.instance.pk:
            grupo = self.instance.groups.filter(name__in=TODOS).first()
            self.fields["perfil"].initial = grupo
        else:
            self.fields["senha"].required = True

    def clean_senha(self):
        senha = self.cleaned_data.get("senha")
        if senha:
            validate_password(senha, self.instance if self.instance.pk else None)
        return senha

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get("senha"):
            usuario.set_password(self.cleaned_data["senha"])
        if commit:
            usuario.save()
            usuario.groups.remove(*Group.objects.filter(name__in=TODOS))
            usuario.groups.add(self.cleaned_data["perfil"])
        return usuario
