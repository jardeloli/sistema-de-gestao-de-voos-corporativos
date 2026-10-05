from django.urls import path

from . import views

app_name = "frota"

urlpatterns = [
    path("", views.AeronaveLista.as_view(), name="aeronaves"),
    path("nova/", views.AeronaveCriar.as_view(), name="aeronave_criar"),
    path("<int:pk>/editar/", views.AeronaveEditar.as_view(), name="aeronave_editar"),
]
