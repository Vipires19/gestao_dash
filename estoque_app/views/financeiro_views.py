"""
Views do dashboard financeiro exclusivo do Emporium Prime e do módulo Títulos.
Rotas: /financeiro/emporium/ (dashboard), /financeiro/titulos/pendentes/, /financeiro/titulos/pagos/.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

from estoque_app.services.financeiro_titulo_service import (
    listar_pendentes,
    listar_pagos,
    obter_titulo_por_id,
    registrar_pagamento as registrar_pagamento_titulo,
)
from estoque_app.services.financeiro_emporium_service import (
    faturamento_hoje_emporium,
    despesas_hoje_emporium,
    lucro_cliente_hoje_emporium,
    lucro_socio_hoje_emporium,
    quantidade_vendas_hoje_emporium,
    grafico_lucro_mes_emporium,
    grafico_despesas_mes_emporium,
    grafico_faturamento_mes_emporium,
    grafico_lucro_3meses_emporium,
    grafico_despesas_3meses_emporium,
    grafico_faturamento_3meses_emporium,
    vendas_emporium_lista,
    alertas_entradas_pendentes,
)


def financeiro_emporium_dashboard(request):
    """
    Dashboard financeiro exclusivo Emporium Prime.
    Rota: /financeiro/emporium/
    Cards (hoje), gráficos (mês e 3 meses), tabela de vendas, alertas de entradas pendentes.
    """
    try:
        fat_hoje = faturamento_hoje_emporium()
        desp_hoje = despesas_hoje_emporium()
        lucro_cli = lucro_cliente_hoje_emporium()
        lucro_soc = lucro_socio_hoje_emporium()
        qtd_vendas = quantidade_vendas_hoje_emporium()
    except Exception as e:
        messages.error(request, f"Erro ao carregar resumo: {e}")
        fat_hoje = desp_hoje = lucro_cli = lucro_soc = 0.0
        qtd_vendas = 0

    try:
        grafico_lucro_mes = grafico_lucro_mes_emporium()
        grafico_despesas_mes = grafico_despesas_mes_emporium()
        grafico_fat_mes = grafico_faturamento_mes_emporium()
    except Exception as e:
        messages.error(request, f"Erro ao carregar gráficos do mês: {e}")
        grafico_lucro_mes = grafico_despesas_mes = grafico_fat_mes = []

    try:
        grafico_lucro_3m = grafico_lucro_3meses_emporium()
        grafico_despesas_3m = grafico_despesas_3meses_emporium()
        grafico_fat_3m = grafico_faturamento_3meses_emporium()
    except Exception as e:
        messages.error(request, f"Erro ao carregar gráficos trimestrais: {e}")
        grafico_lucro_3m = grafico_despesas_3m = grafico_fat_3m = []

    try:
        vendas_lista = vendas_emporium_lista(50)
    except Exception as e:
        messages.error(request, f"Erro ao listar vendas: {e}")
        vendas_lista = []

    try:
        alertas = alertas_entradas_pendentes()
    except Exception as e:
        messages.error(request, f"Erro ao carregar alertas: {e}")
        alertas = {"esta_semana": [], "semana_que_vem": [], "proxima_semana": []}

    lucro_hoje = lucro_cli + lucro_soc

    context = {
        "faturamento_hoje": fat_hoje,
        "despesas_hoje": desp_hoje,
        "lucro_hoje": lucro_hoje,
        "lucro_cliente_hoje": lucro_cli,
        "lucro_socio_hoje": lucro_soc,
        "quantidade_vendas_hoje": qtd_vendas,
        "grafico_lucro_mes": grafico_lucro_mes,
        "grafico_despesas_mes": grafico_despesas_mes,
        "grafico_faturamento_mes": grafico_fat_mes,
        "grafico_lucro_3meses": grafico_lucro_3m,
        "grafico_despesas_3meses": grafico_despesas_3m,
        "grafico_faturamento_3meses": grafico_fat_3m,
        "vendas_lista": vendas_lista,
        "alertas_esta_semana": alertas.get("esta_semana", []),
        "alertas_semana_que_vem": alertas.get("semana_que_vem", []),
        "alertas_proxima_semana": alertas.get("proxima_semana", []),
    }
    return render(request, "estoque_app/financeiro/emporium_dashboard.html", context)


def titulos_pendentes(request):
    """Lista títulos com status PENDENTE. Rota: /financeiro/titulos/pendentes/"""
    from datetime import date
    try:
        titulos = listar_pendentes()
    except Exception as e:
        messages.error(request, f"Erro ao listar títulos: {e}")
        titulos = []
    return render(request, "estoque_app/financeiro/titulos_pendentes.html", {
        "titulos": titulos,
        "hoje": date.today().isoformat(),
    })


def titulos_pagos(request):
    """Lista títulos com status PAGO. Rota: /financeiro/titulos/pagos/"""
    try:
        titulos = listar_pagos()
    except Exception as e:
        messages.error(request, f"Erro ao listar títulos pagos: {e}")
        titulos = []
    return render(request, "estoque_app/financeiro/titulos_pagos.html", {"titulos": titulos})


@require_POST
def titulo_registrar_pagamento(request, titulo_id):
    """Registra o pagamento do título (marca PAGO e salva data). Redireciona para pendentes."""
    data_pagamento = request.POST.get("data_pagamento", "").strip() or None
    titulo = registrar_pagamento_titulo(titulo_id, data_pagamento=data_pagamento)
    if titulo:
        messages.success(request, f"Pagamento registrado. Título R$ {titulo.get('valor', 0):.2f} marcado como PAGO.")
        return redirect("estoque_app:titulos_pendentes")
    messages.error(request, "Título não encontrado ou já pago.")
    return redirect("estoque_app:titulos_pendentes")

