from django.urls import path

from . import views

app_name = "medicao"

urlpatterns = [
    path("medicao/", views.dashboard, name="dashboard"),
    path("medicao/<int:bm_id>/", views.detalhe, name="detalhe"),
    path("medicao/<int:bm_id>/imprimir/<int:periodo_id>/", views.print_periodo, name="print_periodo"),
    path("medicao/<int:bm_id>/consolidado/", views.print_consolidado, name="print_consolidado"),

    path("medicao/api/salvar/", views.api_salvar_boletim, name="api_salvar_boletim"),
    path("medicao/api/excluir/", views.api_excluir_boletim, name="api_excluir_boletim"),

    path("medicao/<int:bm_id>/api/itens/salvar/", views.api_salvar_item, name="api_salvar_item"),
    path("medicao/<int:bm_id>/api/itens/excluir/", views.api_excluir_item, name="api_excluir_item"),

    path("medicao/<int:bm_id>/api/periodos/criar/", views.api_criar_periodo, name="api_criar_periodo"),
    path("medicao/<int:bm_id>/api/periodos/excluir/", views.api_excluir_periodo, name="api_excluir_periodo"),
    path("medicao/<int:bm_id>/api/periodos/editar/",  views.api_editar_periodo,  name="api_editar_periodo"),

    path(
        "medicao/<int:bm_id>/api/medicao/<int:periodo_id>/salvar/",
        views.api_salvar_medicao,
        name="api_salvar_medicao",
    ),
    path("medicao/<int:bm_id>/api/consolidado/", views.api_dados_consolidado, name="api_dados_consolidado"),

    path("medicao/api/servicos/", views.api_autocomplete_servico, name="api_autocomplete_servico"),
]
