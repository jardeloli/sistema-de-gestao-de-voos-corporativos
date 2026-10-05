from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import LoginForm, TrocaSenhaForm, UsuarioForm
from .mixins import PerfilRequeridoMixin


class Login(auth_views.LoginView):
    template_name = "contas/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class Logout(auth_views.LogoutView):
    pass


class TrocarSenha(SuccessMessageMixin, auth_views.PasswordChangeView):
    template_name = "contas/trocar_senha.html"
    form_class = TrocaSenhaForm
    success_url = reverse_lazy("painel:inicio")
    success_message = "Senha alterada."


class UsuarioLista(PerfilRequeridoMixin, ListView):
    acao = "gerenciar_usuarios"
    model = User
    template_name = "contas/usuario_lista.html"
    context_object_name = "usuarios"
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.prefetch_related("groups").order_by("-is_active", "first_name", "username")
        busca = self.request.GET.get("q", "").strip()
        if busca:
            qs = qs.filter(
                Q(first_name__icontains=busca) | Q(last_name__icontains=busca) | Q(username__icontains=busca)
            )
        return qs


class UsuarioCriar(PerfilRequeridoMixin, SuccessMessageMixin, CreateView):
    acao = "gerenciar_usuarios"
    model = User
    form_class = UsuarioForm
    template_name = "contas/usuario_form.html"
    success_url = reverse_lazy("contas:usuarios")
    success_message = "Usuário %(username)s cadastrado."


class UsuarioEditar(PerfilRequeridoMixin, SuccessMessageMixin, UpdateView):
    acao = "gerenciar_usuarios"
    model = User
    form_class = UsuarioForm
    template_name = "contas/usuario_form.html"
    success_url = reverse_lazy("contas:usuarios")
    success_message = "Usuário %(username)s atualizado."

    def form_valid(self, form):
        if form.instance == self.request.user and not form.cleaned_data["is_active"]:
            messages.error(self.request, "Você não pode desativar o próprio usuário.")
            return self.form_invalid(form)
        return super().form_valid(form)
