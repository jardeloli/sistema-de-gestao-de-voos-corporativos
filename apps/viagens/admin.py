from django.contrib import admin

from .models import Abastecimento, Custo, Passageiro, Viagem


class CustoInline(admin.TabularInline):
    model = Custo
    extra = 0


@admin.register(Viagem)
class ViagemAdmin(admin.ModelAdmin):
    list_display = ["data", "horario_previsto", "aeronave", "origem", "destino", "finalidade", "status"]
    list_filter = ["status", "finalidade", "aeronave"]
    search_fields = ["origem", "destino", "descricao"]
    filter_horizontal = ["passageiros"]
    inlines = [CustoInline]
    date_hierarchy = "data"


@admin.register(Passageiro)
class PassageiroAdmin(admin.ModelAdmin):
    list_display = ["nome", "setor", "ativo"]
    search_fields = ["nome", "setor"]


@admin.register(Abastecimento)
class AbastecimentoAdmin(admin.ModelAdmin):
    list_display = ["data", "aeronave", "quantidade_litros", "tipo_combustivel", "valor_total", "local"]
    list_filter = ["aeronave", "tipo_combustivel"]
