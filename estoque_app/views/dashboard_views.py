"""
Views do dashboard.
"""
from django.shortcuts import render
from estoque_app.services.dashboard_service import (
    faturamento_hoje,
    total_vendas_hoje,
    total_produtos_vendidos_hoje,
    total_produtos_estoque_baixo,
    faturamento_ultimos_7_dias,
    top_5_produtos_ultimos_7_dias,
    ultimas_vendas,
    produto_mais_vendido_hoje,
    maior_venda_hoje,
    produtos_estoque_critico,
    alertas_estoque,
    despesas_hoje,
    despesas_ultimos_7_dias,
    lucro_hoje,
    maior_despesa_hoje,
    alertas_financeiros,
)


def dashboard_home(request):
    """
    Rota: /
    Renderiza a home do sistema (dashboard) com cards, gráficos, bloco 3 e bloco 4.
    Inclui despesas, lucro e alertas financeiros.
    """
    fat = faturamento_hoje()
    desp = despesas_hoje()
    lucro = lucro_hoje()
    context = {
        "faturamento_hoje": fat,
        "total_vendas_hoje": total_vendas_hoje(),
        "total_produtos_vendidos_hoje": total_produtos_vendidos_hoje(),
        "produtos_estoque_baixo": total_produtos_estoque_baixo(),
        "despesas_hoje": desp,
        "lucro_hoje": lucro,
        "grafico_faturamento_7_dias": faturamento_ultimos_7_dias(),
        "grafico_despesas_7_dias": despesas_ultimos_7_dias(),
        "top_5_produtos": top_5_produtos_ultimos_7_dias(),
        "ultimas_vendas": ultimas_vendas(5),
        "produto_mais_vendido": produto_mais_vendido_hoje(),
        "maior_venda_hoje": maior_venda_hoje(),
        "maior_despesa_hoje": maior_despesa_hoje(),
        "situacao_dia": "Dia com lucro" if lucro > 0 else "Dia no prejuízo",
        "produtos_criticos": produtos_estoque_critico(10),
        "alertas_estoque": alertas_estoque() + alertas_financeiros(fat, desp, lucro),
    }
    return render(request, "estoque_app/dashboard/home.html", context)
