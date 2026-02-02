"""
URLs do app estoque.

Localização: estoque_app/urls.py

Define as rotas relacionadas a produtos, categorias e vendas.
"""
from django.urls import path, include
from estoque_app.views import dashboard_views, produto_views, categoria_views, venda_views, despesa_views, analise_views, operacao_views, venda_processado_views, venda_caixa_views, venda_emporium_views, financeiro_views, precificacao_views

app_name = 'estoque_app'

urlpatterns = [
    # Dashboard (home)
    path('', dashboard_views.dashboard_home, name='dashboard_home'),
    # Análise
    path('analise/', analise_views.analise_home, name='analise_home'),
    # Produtos
    path('produtos/', produto_views.produto_list, name='produto_list'),
    path('produtos/novo/', produto_views.produto_create, name='produto_create'),
    path('produtos/<str:produto_id>/editar/', produto_views.produto_edit, name='produto_edit'),
    
    # Categorias
    path('categorias/', categoria_views.categoria_list, name='categoria_list'),
    path('categorias/nova/', categoria_views.categoria_create, name='categoria_create'),
    path('categorias/<str:categoria_id>/editar/', categoria_views.categoria_edit, name='categoria_edit'),
    
    # Vendas
    path('vendas/', venda_views.venda_list, name='venda_list'),
    path('vendas/nova/', venda_views.venda_nova, name='venda_nova'),
    path('vendas/<str:venda_id>/', venda_views.venda_detail, name='venda_detail'),
    path('vendas/<str:venda_id>/confirmacao/', venda_views.venda_confirmacao, name='venda_confirmacao'),
    path('vendas/<str:venda_id>/comprovante/', venda_views.venda_comprovante, name='venda_comprovante'),

    # Despesas
    path('despesas/', despesa_views.despesa_list, name='despesa_list'),
    path('despesas/nova/', despesa_views.despesa_create, name='despesa_create'),

    # Operação (entradas de estoque, caixas)
    path('operacao/entradas/', operacao_views.entrada_list, name='entrada_list'),
    path('operacao/entradas/nova/', operacao_views.entrada_nova, name='entrada_nova'),
    path('operacao/caixas/', operacao_views.caixa_list, name='caixa_list'),
    path('operacao/estoque-emporium/', operacao_views.estoque_emporium, name='estoque_emporium'),
    path('operacao/caixas/<str:caixa_id>/', operacao_views.caixa_detail, name='caixa_detail'),
    path('operacao/caixas/<str:caixa_id>/nf/', operacao_views.caixa_nf_download, name='caixa_nf_download'),
    path('operacao/fornecedores/', operacao_views.fornecedor_list, name='fornecedor_list'),
    path('operacao/processamentos/', operacao_views.processamento_list, name='processamento_list'),
    path('operacao/processamentos/novo/', operacao_views.processamento_novo, name='processamento_novo'),

    # Vendas de produtos processados (Fase 3)
    path('vendas-processados/', venda_processado_views.venda_processado_list, name='venda_processado_list'),
    path('vendas-processados/nova/', venda_processado_views.venda_processado_nova, name='venda_processado_nova'),

    # Vendas de caixas (Emporium Prime)
    path('vendas-caixas/', venda_caixa_views.venda_caixa_list, name='venda_caixa_list'),
    path('vendas-caixas/nova/', venda_caixa_views.venda_caixa_nova, name='venda_caixa_nova'),
    path('vendas-caixas/buscar-caixa/', venda_caixa_views.caixa_por_codigo_api, name='caixa_por_codigo_api'),

    # Histórico unificado Emporium Prime (processados + atacado)
    path('vendas-emporium/historico/', venda_emporium_views.venda_emporium_historico, name='venda_emporium_historico'),

    # Financeiro Emporium Prime (dashboard e títulos)
    path('financeiro/emporium/', financeiro_views.financeiro_emporium_dashboard, name='financeiro_emporium_dashboard'),
    path('financeiro/titulos/pendentes/', financeiro_views.titulos_pendentes, name='titulos_pendentes'),
    path('financeiro/titulos/pagos/', financeiro_views.titulos_pagos, name='titulos_pagos'),
    path('financeiro/titulos/<str:titulo_id>/registrar-pagamento/', financeiro_views.titulo_registrar_pagamento, name='titulo_registrar_pagamento'),
    path('emporium/vendas/<str:venda_id>/comprovante/', venda_emporium_views.emporium_comprovante, name='emporium_comprovante'),

    # Precificação Emporium Prime (produto comercial)
    path('precificacao/emporium/', precificacao_views.precificacao_list, name='precificacao_list'),
    path('precificacao/emporium/nova/', precificacao_views.precificacao_nova, name='precificacao_nova'),
    path('precificacao/emporium/tabela-pdf/', precificacao_views.precificacao_tabela_pdf, name='precificacao_tabela_pdf'),

    # Módulo PÃES
    path('paes/', include('estoque_app.paes.urls')),
]
