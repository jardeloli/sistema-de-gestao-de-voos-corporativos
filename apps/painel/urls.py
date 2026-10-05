from django.urls import path

from . import views

app_name = "painel"

urlpatterns = [
    path("", views.Inicio.as_view(), name="inicio"),
    path("indicadores/", views.Dashboard.as_view(), name="dashboard"),
]
