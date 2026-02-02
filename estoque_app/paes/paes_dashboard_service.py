"""
Service do Dashboard do módulo PÃES.
Agregações, contagens, produção e resumos financeiros — somente planos ATIVOS.
"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any

from estoque_app.paes.entrega_pao_service import (
    gerar_entregas_para_periodo,
    listar_entregas_por_data,
    resumo_producao_por_data,
)
from estoque_app.paes.titulo_receber_pao_service import (
    gerar_titulos_para_periodo,
    listar_pendentes_agrupados,
    get_titulos_collection,
)
from core.database import get_database


def _hoje():
    return date.today()


def _semana_atual():
    """Retorna (segunda-feira, domingo) da semana atual."""
    hoje = _hoje()
    seg = hoje - timedelta(days=hoje.weekday())
    dom = seg + timedelta(days=6)
    return seg, dom


def _ensure_dados_periodo():
    """Garante entregas e títulos gerados para o período relevante (hoje até +7 dias, títulos +30)."""
    hoje = _hoje()
    fim_entregas = hoje + timedelta(days=7)
    fim_titulos = hoje + timedelta(days=30)
    gerar_entregas_para_periodo(hoje, fim_entregas)
    gerar_titulos_para_periodo(hoje, fim_titulos)


# ---------- BLOCO 1 — CARDS ----------

def get_dashboard_cards() -> Dict[str, Any]:
    """
    Retorna dados para os 6 cards: operacional (entregas hoje/amanhã) e financeiro
    (receber hoje, receber semana, planos em atraso).
    Somente planos ATIVOS (entregas/títulos já vêm de planos ativos).
    """
    _ensure_dados_periodo()
    hoje = _hoje()
    amanha = hoje + timedelta(days=1)
    seg, dom = _semana_atual()

    # Operacional
    entregas_hoje = listar_entregas_por_data(hoje)
    entregas_amanha = listar_entregas_por_data(amanha)
    clientes_hoje = len(set(e.get("cliente_id") for e in entregas_hoje))
    clientes_amanha = len(set(e.get("cliente_id") for e in entregas_amanha))
    paes_hoje = sum(e.get("quantidade_paes") or 0 for e in entregas_hoje)
    paes_amanha = sum(e.get("quantidade_paes") or 0 for e in entregas_amanha)

    # Financeiro: receber hoje / esta semana / em atraso
    coll = get_titulos_collection()
    d_hoje_ini = datetime(hoje.year, hoje.month, hoje.day)
    d_hoje_fim = datetime(hoje.year, hoje.month, hoje.day, 23, 59, 59, 999999)
    d_seg = datetime(seg.year, seg.month, seg.day)
    d_dom = datetime(dom.year, dom.month, dom.day, 23, 59, 59, 999999)

    receber_hoje = 0.0
    for doc in coll.find({"status": "PENDENTE", "data_vencimento": {"$gte": d_hoje_ini, "$lte": d_hoje_fim}}):
        receber_hoje += float(doc.get("valor") or 0)

    receber_semana = 0.0
    for doc in coll.find({"status": "PENDENTE", "data_vencimento": {"$gte": d_seg, "$lte": d_dom}}):
        receber_semana += float(doc.get("valor") or 0)

    em_atraso_qtd = 0
    em_atraso_valor = 0.0
    for doc in coll.find({"status": "PENDENTE"}):
        dv = doc.get("data_vencimento")
        if not dv:
            continue
        d_venc = dv.date() if hasattr(dv, "date") else dv
        if d_venc < hoje:
            em_atraso_qtd += 1
            em_atraso_valor += float(doc.get("valor") or 0)

    return {
        "operacional": {
            "entregas_hoje_clientes": clientes_hoje,
            "entregas_hoje_paes": paes_hoje,
            "entregas_amanha_clientes": clientes_amanha,
            "entregas_amanha_paes": paes_amanha,
            "total_paes_amanha": paes_amanha,
        },
        "financeiro": {
            "receber_hoje": round(receber_hoje, 2),
            "receber_semana": round(receber_semana, 2),
            "planos_atraso_quantidade": em_atraso_qtd,
            "planos_atraso_valor": round(em_atraso_valor, 2),
        },
    }


# ---------- BLOCO 2 — GRÁFICOS ----------

def get_grafico_paes_por_dia(dias: int = 7) -> List[Dict[str, Any]]:
    """
    Pães por dia nos últimos `dias` dias.
    Eixo X: datas, Eixo Y: quantidade (soma de todas as entregas daquele dia).
    """
    _ensure_dados_periodo()
    hoje = _hoje()
    resultado = []
    for i in range(dias - 1, -1, -1):
        d = hoje - timedelta(days=i)
        entregas = listar_entregas_por_data(d)
        total = sum(e.get("quantidade_paes") or 0 for e in entregas)
        resultado.append({
            "data_iso": d.isoformat(),
            "data_fmt": d.strftime("%d/%m"),
            "quantidade": total,
        })
    return resultado


def get_grafico_recebimentos_semana() -> Dict[str, float]:
    """
    Recebimentos na semana atual: recebido (PAGO), a_receber (PENDENTE na semana), em_atraso (PENDENTE vencido antes da semana).
    """
    _ensure_dados_periodo()
    seg, dom = _semana_atual()
    d_seg = datetime(seg.year, seg.month, seg.day)
    d_dom = datetime(dom.year, dom.month, dom.day, 23, 59, 59, 999999)
    coll = get_titulos_collection()

    recebido = 0.0
    for doc in coll.find({"status": "PAGO", "data_pagamento": {"$gte": d_seg, "$lte": d_dom}}):
        recebido += float(doc.get("valor") or 0)

    a_receber = 0.0
    for doc in coll.find({"status": "PENDENTE", "data_vencimento": {"$gte": d_seg, "$lte": d_dom}}):
        a_receber += float(doc.get("valor") or 0)

    em_atraso = 0.0
    for doc in coll.find({"status": "PENDENTE", "data_vencimento": {"$lt": d_seg}}):
        em_atraso += float(doc.get("valor") or 0)

    return {
        "recebido": round(recebido, 2),
        "a_receber": round(a_receber, 2),
        "em_atraso": round(em_atraso, 2),
    }


# ---------- BLOCO 3 — ENTREGAS HOJE / AMANHÃ ----------

def get_entregas_hoje() -> List[Dict[str, Any]]:
    """Lista entregas de hoje (com nome, endereço, tipo_plano)."""
    _ensure_dados_periodo()
    return listar_entregas_por_data(_hoje())


def get_entregas_amanha() -> List[Dict[str, Any]]:
    """Lista entregas de amanhã."""
    _ensure_dados_periodo()
    return listar_entregas_por_data(_hoje() + timedelta(days=1))


# ---------- BLOCO 4 — PRODUÇÃO PARA AMANHÃ ----------

def get_producao_amanha() -> Dict[str, Any]:
    """
    Produção para amanhã: cada entrega = 1 saco (tamanho = quantidade_paes).
    Retorna itens [(qtd_paes, num_sacos), ...] ordenados e total_paes.
    """
    _ensure_dados_periodo()
    amanha = _hoje() + timedelta(days=1)
    return resumo_producao_por_data(amanha)


# ---------- BLOCO 5 — ALERTAS FINANCEIROS ----------

def get_alertas_financeiros() -> Dict[str, List[Dict[str, Any]]]:
    """
    Em atraso: cliente, valor, dias_atraso.
    A receber esta semana: data, cliente, valor.
    Itens já enriquecidos (nome_cliente, data_vencimento_fmt, dias_atraso).
    """
    _ensure_dados_periodo()
    agrupado = listar_pendentes_agrupados()
    return {
        "em_atraso": agrupado["em_atraso"],
        "a_receber_semana": agrupado["esta_semana"],
    }


# ---------- CONTEXTO COMPLETO DO DASHBOARD ----------

def get_dashboard_context() -> Dict[str, Any]:
    """Retorna todo o contexto necessário para a view do dashboard (view fina)."""
    cards = get_dashboard_cards()
    grafico_paes = get_grafico_paes_por_dia(7)
    grafico_recebimentos = get_grafico_recebimentos_semana()
    entregas_hoje = get_entregas_hoje()
    entregas_amanha = get_entregas_amanha()
    producao_amanha = get_producao_amanha()
    alertas = get_alertas_financeiros()
    hoje = _hoje()
    amanha = hoje + timedelta(days=1)
    return {
        "cards": cards,
        "grafico_paes": grafico_paes,
        "grafico_recebimentos": grafico_recebimentos,
        "entregas_hoje": entregas_hoje,
        "entregas_amanha": entregas_amanha,
        "producao_amanha": producao_amanha,
        "em_atraso": alertas["em_atraso"],
        "a_receber_semana": alertas["a_receber_semana"],
        "hoje_fmt": hoje.strftime("%d/%m/%Y"),
        "amanha_fmt": amanha.strftime("%d/%m/%Y"),
        "amanha_iso": amanha.isoformat(),
    }
