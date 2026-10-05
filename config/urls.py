from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("apps.painel.urls")),
    path("conta/", include("apps.contas.urls")),
    path("aeronaves/", include("apps.frota.urls")),
    path("viagens/", include("apps.viagens.urls")),
    path("admin/", admin.site.urls),
]

handler403 = "apps.painel.erros.acesso_negado"
handler404 = "apps.painel.erros.nao_encontrado"
