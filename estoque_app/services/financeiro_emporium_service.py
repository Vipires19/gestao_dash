"""
Service para dashboard financeiro exclusivo do Emporium Prime.
Considera: vendas de caixas, vendas de processados; despesas e alertas vêm dos títulos financeiros.
Despesas: apenas títulos com status PAGO (data_pagamento).
Alertas: apenas títulos com status PENDENTE.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from core.database import get_database

from estoque_app.services.financeiro_titulo_service import (
    despesas_titulos_hoje,
    despesas_titulos_por_dia,
    grafico_despesas_titulos_mes,
    grafico_despesas_titulos_3meses,
    alertas_titulos_pendentes,
)


def _hoje_date():
    """Retorna a data de hoje (date) em UTC."""
    return datetime.utcnow().date()


def _normalizar_data(d):
    """Retorna date a partir de datetime ou date."""
    if d is None:
        return None
    if hasattr(d, "date"):
        return d.date() if hasattr(d, "date") and callable(getattr(d, "date")) else d
    return d


def faturamento_hoje_emporium() -> float:
    """Faturamento hoje: soma valor_total_venda das vendas Emporium (processados + caixas) com data_venda = hoje."""
    db = get_database()
    hoje = _hoje_date()
    inicio = datetime(hoje.year, hoje.month, hoje.day, 0, 0, 0, 0)
    fim = datetime(hoje.year, hoje.month, hoje.day, 23, 59, 59, 999000)
    total = 0.0
    for doc in db["vendas"].find({"tipo_venda": {"$exists": True}, "data_venda": {"$gte": inicio, "$lte": fim}}):
        r = doc.get("resumo_financeiro") or {}
        total += float(r.get("valor_total_venda", 0) or doc.get("valor_total_venda", 0))
    for doc in db["vendas_caixas"].find({"data_venda": {"$gte": inicio, "$lte": fim}}):
        r = doc.get("resumo_financeiro") or {}
        total += float(r.get("valor_total_venda", 0))
    return round(total, 2)


def despesas_hoje_emporium() -> float:
    """Despesas hoje: soma de títulos financeiros PAGO com data_pagamento = hoje."""
    return despesas_titulos_hoje()


def lucro_cliente_hoje_emporium() -> float:
    """Soma lucro_cliente das vendas Emporium hoje."""
    db = get_database()
    hoje = _hoje_date()
    inicio = datetime(hoje.year, hoje.month, hoje.day, 0, 0, 0, 0)
    fim = datetime(hoje.year, hoje.month, hoje.day, 23, 59, 59, 999000)
    total = 0.0
    for doc in db["vendas"].find({"tipo_venda": {"$exists": True}, "data_venda": {"$gte": inicio, "$lte": fim}}):
        div = doc.get("divisao_lucro") or {}
        total += float(div.get("lucro_cliente", 0))
    for doc in db["vendas_caixas"].find({"data_venda": {"$gte": inicio, "$lte": fim}}):
        div = doc.get("divisao_lucro") or {}
        total += float(div.get("lucro_cliente", 0))
    return round(total, 2)


def lucro_socio_hoje_emporium() -> float:
    """Soma lucro_socio das vendas Emporium hoje."""
    db = get_database()
    hoje = _hoje_date()
    inicio = datetime(hoje.year, hoje.month, hoje.day, 0, 0, 0, 0)
    fim = datetime(hoje.year, hoje.month, hoje.day, 23, 59, 59, 999000)
    total = 0.0
    for doc in db["vendas"].find({"tipo_venda": {"$exists": True}, "data_venda": {"$gte": inicio, "$lte": fim}}):
        div = doc.get("divisao_lucro") or {}
        total += float(div.get("lucro_socio", 0))
    for doc in db["vendas_caixas"].find({"data_venda": {"$gte": inicio, "$lte": fim}}):
        div = doc.get("divisao_lucro") or {}
        total += float(div.get("lucro_socio", 0))
    return round(total, 2)


def quantidade_vendas_hoje_emporium() -> int:
    """Quantidade de vendas Emporium hoje (processados + caixas)."""
    db = get_database()
    hoje = _hoje_date()
    inicio = datetime(hoje.year, hoje.month, hoje.day, 0, 0, 0, 0)
    fim = datetime(hoje.year, hoje.month, hoje.day, 23, 59, 59, 999000)
    n = db["vendas"].count_documents({"tipo_venda": {"$exists": True}, "data_venda": {"$gte": inicio, "$lte": fim}})
    n += db["vendas_caixas"].count_documents({"data_venda": {"$gte": inicio, "$lte": fim}})
    return n


def _mes_atual_range():
    """Início e fim do mês atual (UTC)."""
    now = datetime.utcnow()
    inicio = datetime(now.year, now.month, 1, 0, 0, 0, 0)
    if now.month == 12:
        fim = datetime(now.year, 12, 31, 23, 59, 59, 999000)
    else:
        fim = datetime(now.year, now.month + 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
    return inicio, fim


def _tres_meses_range():
    """Início e fim dos últimos 3 meses (UTC)."""
    now = datetime.utcnow()
    fim = datetime(now.year, now.month, now.day, 23, 59, 59, 999000)
    inicio = now - timedelta(days=92)
    inicio = datetime(inicio.year, inicio.month, 1, 0, 0, 0, 0)
    return inicio, fim


def grafico_lucro_mes_emporium() -> List[Dict[str, Any]]:
    """Lucro por dia no mês atual (vendas Emporium - despesas do dia de títulos PAGO)."""
    db = get_database()
    inicio, fim = _mes_atual_range()
    vendas = db["vendas"]
    vc = db["vendas_caixas"]
    from calendar import monthrange
    _, ultimo = monthrange(inicio.year, inicio.month)
    desp_por_dia = despesas_titulos_por_dia(inicio, fim)
    por_dia = {}
    for d in range(1, ultimo + 1):
        di = datetime(inicio.year, inicio.month, d, 0, 0, 0, 0)
        df = datetime(inicio.year, inicio.month, d, 23, 59, 59, 999000)
        lucro = 0.0
        for doc in vendas.find({"tipo_venda": {"$exists": True}, "data_venda": {"$gte": di, "$lte": df}}):
            div = doc.get("divisao_lucro") or {}
            lucro += float(div.get("lucro_cliente", 0)) + float(div.get("lucro_socio", 0))
        for doc in vc.find({"data_venda": {"$gte": di, "$lte": df}}):
            div = doc.get("divisao_lucro") or {}
            lucro += float(div.get("lucro_cliente", 0)) + float(div.get("lucro_socio", 0))
        lucro -= desp_por_dia.get(d, 0)
        por_dia[d] = round(lucro, 2)
    return [{"data": f"{d:02d}/{inicio.month:02d}", "valor": por_dia.get(d, 0)} for d in range(1, ultimo + 1)]


def grafico_despesas_mes_emporium() -> List[Dict[str, Any]]:
    """Despesas por dia no mês atual (títulos PAGO)."""
    return grafico_despesas_titulos_mes()


def grafico_faturamento_mes_emporium() -> List[Dict[str, Any]]:
    """Faturamento por dia no mês atual (vendas Emporium)."""
    db = get_database()
    inicio, fim = _mes_atual_range()
    from calendar import monthrange
    _, ultimo = monthrange(inicio.year, inicio.month)
    por_dia = {}
    for d in range(1, ultimo + 1):
        di = datetime(inicio.year, inicio.month, d, 0, 0, 0, 0)
        df = datetime(inicio.year, inicio.month, d, 23, 59, 59, 999000)
        total = 0.0
        for doc in db["vendas"].find({"tipo_venda": {"$exists": True}, "data_venda": {"$gte": di, "$lte": df}}):
            r = doc.get("resumo_financeiro") or {}
            total += float(r.get("valor_total_venda", 0) or doc.get("valor_total_venda", 0))
        for doc in db["vendas_caixas"].find({"data_venda": {"$gte": di, "$lte": df}}):
            r = doc.get("resumo_financeiro") or {}
            total += float(r.get("valor_total_venda", 0))
        por_dia[d] = round(total, 2)
    return [{"data": f"{d:02d}/{inicio.month:02d}", "valor": por_dia.get(d, 0)} for d in range(1, ultimo + 1)]


def grafico_lucro_3meses_emporium() -> List[Dict[str, Any]]:
    """Lucro por mês (últimos 3 meses): vendas Emporium - despesas de títulos PAGO."""
    db = get_database()
    now = datetime.utcnow()
    vendas = db["vendas"]
    vc = db["vendas_caixas"]
    titulos = db["financeiro_titulos"]
    saida = []
    for i in range(2, -1, -1):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        di = datetime(y, m, 1, 0, 0, 0, 0)
        if m == 12:
            df = datetime(y, 12, 31, 23, 59, 59, 999000)
        else:
            df = datetime(y, m + 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
        lucro = 0.0
        for doc in vendas.find({"tipo_venda": {"$exists": True}, "data_venda": {"$gte": di, "$lte": df}}):
            div = doc.get("divisao_lucro") or {}
            lucro += float(div.get("lucro_cliente", 0)) + float(div.get("lucro_socio", 0))
        for doc in vc.find({"data_venda": {"$gte": di, "$lte": df}}):
            div = doc.get("divisao_lucro") or {}
            lucro += float(div.get("lucro_cliente", 0)) + float(div.get("lucro_socio", 0))
        desp_res = list(titulos.aggregate([
            {"$match": {"status": "PAGO", "data_pagamento": {"$gte": di, "$lte": df}}},
            {"$group": {"_id": None, "total": {"$sum": "$valor"}}},
        ]))
        if desp_res and desp_res[0].get("total"):
            lucro -= float(desp_res[0]["total"])
        saida.append({"data": f"{m:02d}/{y}", "valor": round(lucro, 2)})
    return saida


def grafico_despesas_3meses_emporium() -> List[Dict[str, Any]]:
    """Despesas por mês (últimos 3 meses) — títulos PAGO."""
    return grafico_despesas_titulos_3meses()


def grafico_faturamento_3meses_emporium() -> List[Dict[str, Any]]:
    """Faturamento por mês (últimos 3 meses) vendas Emporium."""
    db = get_database()
    inicio, fim = _tres_meses_range()
    now = datetime.utcnow()
    saida = []
    for i in range(2, -1, -1):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        di = datetime(y, m, 1, 0, 0, 0, 0)
        if m == 12:
            df = datetime(y, 12, 31, 23, 59, 59, 999000)
        else:
            df = datetime(y, m + 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
        total = 0.0
        for doc in db["vendas"].find({"tipo_venda": {"$exists": True}, "data_venda": {"$gte": di, "$lte": df}}):
            r = doc.get("resumo_financeiro") or {}
            total += float(r.get("valor_total_venda", 0) or doc.get("valor_total_venda", 0))
        for doc in db["vendas_caixas"].find({"data_venda": {"$gte": di, "$lte": df}}):
            r = doc.get("resumo_financeiro") or {}
            total += float(r.get("valor_total_venda", 0))
        saida.append({"data": f"{m:02d}/{y}", "valor": round(total, 2)})
    return saida


def vendas_emporium_lista(limit: int = 50) -> List[Dict[str, Any]]:
    """Lista vendas Emporium (processados + caixas) para tabela: Data | Tipo | Valor total | Lucro cliente | Lucro sócio."""
    db = get_database()
    saida = []
    for doc in db["vendas"].find({"tipo_venda": {"$exists": True}}).sort([("data_venda", -1), ("created_at", -1)]).limit(limit):
        doc["id"] = str(doc["_id"])
        doc["tipo_emporium"] = "PROCESSADO"
        dv = doc.get("data_venda")
        doc["data_venda_fmt"] = dv.strftime("%d/%m/%Y") if dv and hasattr(dv, "strftime") else ""
        r = doc.get("resumo_financeiro") or {}
        doc["valor_total_venda"] = float(r.get("valor_total_venda", 0) or doc.get("valor_total_venda", 0))
        div = doc.get("divisao_lucro") or {}
        doc["lucro_cliente"] = float(div.get("lucro_cliente", 0))
        doc["lucro_socio"] = float(div.get("lucro_socio", 0))
        saida.append(doc)
    for doc in db["vendas_caixas"].find().sort([("data_venda", -1), ("created_at", -1)]).limit(limit):
        doc["id"] = str(doc["_id"])
        doc["tipo_emporium"] = "ATACADO"
        dv = doc.get("data_venda")
        doc["data_venda_fmt"] = dv.strftime("%d/%m/%Y") if dv and hasattr(dv, "strftime") else ""
        r = doc.get("resumo_financeiro") or {}
        doc["valor_total_venda"] = float(r.get("valor_total_venda", 0))
        div = doc.get("divisao_lucro") or {}
        doc["lucro_cliente"] = float(div.get("lucro_cliente", 0))
        doc["lucro_socio"] = float(div.get("lucro_socio", 0))
        saida.append(doc)
    saida.sort(key=lambda x: (x.get("data_venda") or datetime.min, x.get("created_at") or datetime.min), reverse=True)
    return saida[:limit]


def alertas_entradas_pendentes() -> Dict[str, List[Dict[str, Any]]]:
    """
    Alertas de títulos PENDENTE (obrigações a pagar).
    Agrupa em: esta_semana, semana_que_vem, proxima_semana (por data_vencimento).
    """
    return alertas_titulos_pendentes()
