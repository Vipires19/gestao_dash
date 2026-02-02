"""
URLs do módulo PÃES.
Incluído no urls.py principal com prefixo /paes/
"""
from django.urls import path
from estoque_app.paes import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="paes_dashboard"),
    path("clientes/", views.clientes_list, name="paes_clientes_list"),
    path("clientes/novo/", views.clientes_novo, name="paes_clientes_novo"),
    path("clientes/<str:cliente_id>/editar/", views.clientes_editar, name="paes_clientes_editar"),
    path("clientes/<str:cliente_id>/inativar/", views.clientes_inativar, name="paes_clientes_inativar"),
    path("planos/", views.planos_list, name="paes_planos_list"),
    path("planos/novo/", views.planos_novo, name="paes_planos_novo"),
    path("planos/<str:plano_id>/editar/", views.planos_editar, name="paes_planos_editar"),
    path("planos/<str:plano_id>/cancelar/", views.planos_cancelar, name="paes_planos_cancelar"),
    path("entregas/", views.entregas_list, name="paes_entregas_list"),
    path("producao/pdf/", views.ordem_producao_pdf, name="paes_ordem_producao_pdf"),
    path("entregas/confirmar/<str:entrega_id>/", views.entrega_confirmar, name="paes_entrega_confirmar"),
    path("financeiro/pendentes/", views.financeiro_pendentes, name="paes_financeiro_pendentes"),
    path("financeiro/pagos/", views.financeiro_pagos, name="paes_financeiro_pagos"),
    path("financeiro/registrar/<str:titulo_id>/", views.financeiro_registrar, name="paes_financeiro_registrar"),
]
