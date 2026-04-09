from django.contrib import admin
from .models import Obra, Orcamento, ItemMaterial, ItemServico


class ItemMaterialInline(admin.TabularInline):
    model = ItemMaterial
    extra = 0
    readonly_fields = ("valor_total",)


class ItemServicoInline(admin.TabularInline):
    model = ItemServico
    extra = 0
    readonly_fields = ("valor_total",)


class OrcamentoInline(admin.TabularInline):
    model = Orcamento
    extra = 0
    show_change_link = True


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "projeto", "criado_em")
    list_filter = ("cliente",)
    search_fields = ("nome",)
    inlines = [OrcamentoInline]


@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "obra", "criado_em")
    search_fields = ("nome", "obra__nome")
    inlines = [ItemMaterialInline, ItemServicoInline]


@admin.register(ItemMaterial)
class ItemMaterialAdmin(admin.ModelAdmin):
    list_display = ("produto", "orcamento", "quantidade", "valor_unitario", "valor_total")
    list_select_related = ("produto", "orcamento")


@admin.register(ItemServico)
class ItemServicoAdmin(admin.ModelAdmin):
    list_display = ("servico", "orcamento", "quantidade", "valor_unitario", "valor_total")
    list_select_related = ("servico", "orcamento")
