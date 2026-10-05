from django.contrib import admin

from .models import Aeronave


@admin.register(Aeronave)
class AeronaveAdmin(admin.ModelAdmin):
    list_display = ["prefixo", "modelo", "identificacao", "capacidade_passageiros", "ativa"]
    list_filter = ["ativa"]
    search_fields = ["prefixo", "modelo", "identificacao"]
