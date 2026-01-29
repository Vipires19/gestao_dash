"""
URLs do app estoque.

Localização: estoque_app/urls.py

Define as rotas relacionadas a produtos, categorias e vendas.
"""
from django.urls import path
from estoque_app.views import dashboard_views, produto_views, categoria_views, venda_views, despesa_views, analise_views

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
]
