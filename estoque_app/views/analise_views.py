"""
Views da página de Análise (dashboard por período).
"""
from django.shortcuts import render
from estoque_app.services.dashboard_service import (
    resumo_periodo,
    grafico_faturamento_periodo,
    grafico_despesas_periodo,
    insights_periodo,
)


PERIODOS_VALIDOS = ("mes", "trimestre", "geral")


def analise_home(request):
    """
    Rota: /analise/
    Dashboard de análise por período. Filtro via querystring: ?periodo=mes|trimestre|geral
    Default: periodo=mes
    """
    periodo = request.GET.get("periodo", "mes").strip().lower()
    if periodo not in PERIODOS_VALIDOS:
        periodo = "mes"

    resumo = resumo_periodo(periodo)
    grafico_fat = grafico_faturamento_periodo(periodo)
    grafico_desp = grafico_despesas_periodo(periodo)
    insights = insights_periodo(periodo)

    context = {
        "periodo": periodo,
        "faturamento": resumo["faturamento"],
        "despesas": resumo["despesas"],
        "lucro": resumo["lucro"],
        "total_vendas": resumo["total_vendas"],
        "grafico_faturamento": grafico_fat,
        "grafico_despesas": grafico_desp,
        "produto_mais_vendido": insights["produto_mais_vendido"],
        "maior_venda": insights["maior_venda"],
        "maior_despesa": insights["maior_despesa"],
    }
    return render(request, "estoque_app/analise/home.html", context)
