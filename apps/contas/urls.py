from django.urls import path

from . import views

app_name = "contas"

urlpatterns = [
    path("entrar/", views.Login.as_view(), name="login"),
    path("sair/", views.Logout.as_view(), name="logout"),
    path("senha/", views.TrocarSenha.as_view(), name="trocar_senha"),
    path("usuarios/", views.UsuarioLista.as_view(), name="usuarios"),
    path("usuarios/novo/", views.UsuarioCriar.as_view(), name="usuario_criar"),
    path("usuarios/<int:pk>/editar/", views.UsuarioEditar.as_view(), name="usuario_editar"),
]
