from django.urls import path

from . import views

app_name = "viagens"

urlpatterns = [
    path("", views.ViagemLista.as_view(), name="lista"),
    path("nova/", views.ViagemCriar.as_view(), name="criar"),
    path("<int:pk>/", views.ViagemDetalhe.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.ViagemEditar.as_view(), name="editar"),
    path("<int:pk>/cancelar/", views.ViagemCancelar.as_view(), name="cancelar"),
    path("<int:pk>/registrar-voo/", views.ViagemConcluir.as_view(), name="concluir"),
    path("<int:pk>/custos/novo/", views.CustoCriar.as_view(), name="custo_criar"),
    path("custos/<int:pk>/excluir/", views.CustoExcluir.as_view(), name="custo_excluir"),
    path("abastecimentos/", views.AbastecimentoLista.as_view(), name="abastecimentos"),
    path("abastecimentos/novo/", views.AbastecimentoCriar.as_view(), name="abastecimento_criar"),
    path("abastecimentos/<int:pk>/editar/", views.AbastecimentoEditar.as_view(), name="abastecimento_editar"),
    path("passageiros/", views.PassageiroLista.as_view(), name="passageiros"),
    path("passageiros/novo/", views.PassageiroCriar.as_view(), name="passageiro_criar"),
    path("passageiros/<int:pk>/editar/", views.PassageiroEditar.as_view(), name="passageiro_editar"),
]
