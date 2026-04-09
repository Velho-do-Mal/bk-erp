from django.urls import path
from . import views

app_name = "orcamento"

urlpatterns = [
    path("orcamento/", views.dashboard, name="dashboard"),
    path("orcamento/salvar-obra/", views.salvar_obra, name="salvar_obra"),
    path("orcamento/autocomplete-produto/", views.autocomplete_produto, name="autocomplete_produto"),
    path("orcamento/autocomplete-servico/", views.autocomplete_servico, name="autocomplete_servico"),
    path("orcamento/salvar-item-material/", views.salvar_item_material, name="salvar_item_material"),
    path("orcamento/excluir-item-material/", views.excluir_item_material, name="excluir_item_material"),
    path("orcamento/salvar-item-servico/", views.salvar_item_servico, name="salvar_item_servico"),
    path("orcamento/excluir-item-servico/", views.excluir_item_servico, name="excluir_item_servico"),
    path("orcamento/exportar-excel/<int:orcamento_id>/", views.exportar_excel, name="exportar_excel"),
]
