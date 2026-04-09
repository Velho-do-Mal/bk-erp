from django.contrib import admin
from .models import BoletimMedicao, ItemContrato, PeriodoMedicao, MedicaoItem


class ItemContratoInline(admin.TabularInline):
    model = ItemContrato
    extra = 0
    fields = ("ordem", "codigo", "descricao", "quantidade_total", "unidade", "preco_unitario")


class MedicaoItemInline(admin.TabularInline):
    model = MedicaoItem
    extra = 0
    fields = ("item", "quantidade_medida")


@admin.register(BoletimMedicao)
class BoletimMedicaoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "cliente", "projeto", "contrato", "criado_em")
    list_filter = ("cliente",)
    search_fields = ("nome", "contrato", "codigo_obra")
    inlines = [ItemContratoInline]


@admin.register(PeriodoMedicao)
class PeriodoMedicaoAdmin(admin.ModelAdmin):
    list_display = ("id", "boletim", "numero", "data_inicio", "data_fim")
    list_filter = ("boletim",)
    inlines = [MedicaoItemInline]


@admin.register(ItemContrato)
class ItemContratoAdmin(admin.ModelAdmin):
    list_display = ("id", "boletim", "codigo", "descricao", "quantidade_total", "unidade", "preco_unitario")
    list_filter = ("boletim",)


@admin.register(MedicaoItem)
class MedicaoItemAdmin(admin.ModelAdmin):
    list_display = ("id", "periodo", "item", "quantidade_medida")
