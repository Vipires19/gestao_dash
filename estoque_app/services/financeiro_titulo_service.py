"""
Service para títulos financeiros (obrigações geradas pelas entradas de estoque).
O financeiro NÃO cria despesas manualmente; apenas registra pagamento de títulos.
Collection: financeiro_titulos
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database


def get_titulos_collection():
    """Retorna a collection financeiro_titulos."""
    return get_database()["financeiro_titulos"]


def criar_titulo_para_entrada(
    entrada_id,
    valor: float,
    data_vencimento=None,
) -> Dict[str, Any]:
    """
    Cria um título financeiro com status PENDENTE associado à entrada.
    Chamado automaticamente ao registrar uma entrada de estoque.
    entrada_id: ObjectId ou str
    valor: valor total da obrigação
    data_vencimento: opcional, data prevista de pagamento
    """
    coll = get_titulos_collection()
    if isinstance(entrada_id, str):
        try:
            entrada_id = ObjectId(entrada_id)
        except Exception:
            raise ValueError("ID da entrada inválido.")
    if valor is None or valor < 0:
        raise ValueError("Valor do título inválido.")
    now = datetime.utcnow()
    data_venc_dt = None
    if data_vencimento:
        if hasattr(data_vencimento, "strftime"):
            data_venc_dt = data_vencimento
        else:
            try:
                data_venc_dt = datetime.strptime(str(data_vencimento)[:10], "%Y-%m-%d")
            except Exception:
                pass
    doc = {
        "entrada_id": entrada_id,
        "valor": round(float(valor), 2),
        "status": "PENDENTE",
        "data_vencimento": data_venc_dt,
        "data_pagamento": None,
        "created_at": now,
    }
    result = coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    return doc


def _enriquecer_titulo(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Adiciona id, datas formatadas e dados da entrada (fornecedor, NF)."""
    doc["id"] = str(doc["_id"])
    db = get_database()
    entrada_id = doc.get("entrada_id")
    if entrada_id:
        entrada = db["entradas_estoque"].find_one({"_id": ObjectId(entrada_id) if isinstance(entrada_id, str) else entrada_id})
        if entrada:
            doc["data_entrada"] = entrada.get("data_entrada")
            doc["data_entrada_fmt"] = entrada["data_entrada"].strftime("%d/%m/%Y") if entrada.get("data_entrada") and hasattr(entrada["data_entrada"], "strftime") else ""
            fid = entrada.get("fornecedor_id")
            f = db["fornecedores"].find_one({"_id": fid}) if fid else None
            doc["nome_fornecedor"] = f.get("nome", "") if f else ""
            nf = entrada.get("nf_e") or {}
            doc["nf_numero"] = nf.get("numero", "")
        else:
            doc["data_entrada_fmt"] = ""
            doc["nome_fornecedor"] = ""
            doc["nf_numero"] = ""
    else:
        doc["data_entrada_fmt"] = ""
        doc["nome_fornecedor"] = ""
        doc["nf_numero"] = ""
    dv = doc.get("data_vencimento")
    doc["data_vencimento_fmt"] = dv.strftime("%d/%m/%Y") if dv and hasattr(dv, "strftime") else ""
    dp = doc.get("data_pagamento")
    doc["data_pagamento_fmt"] = dp.strftime("%d/%m/%Y") if dp and hasattr(dp, "strftime") else ""
    return doc


def listar_pendentes() -> List[Dict[str, Any]]:
    """Lista títulos com status PENDENTE, ordenados por data_vencimento (null por último) e created_at."""
    coll = get_titulos_collection()
    cursor = coll.find({"status": "PENDENTE"}).sort([
        ("data_vencimento", 1),
        ("created_at", 1),
    ])
    saida = []
    for doc in cursor:
        _enriquecer_titulo(doc)
        saida.append(doc)
    return saida


def listar_pagos(limit: int = 200) -> List[Dict[str, Any]]:
    """Lista títulos com status PAGO, ordenados por data_pagamento desc."""
    coll = get_titulos_collection()
    cursor = coll.find({"status": "PAGO"}).sort("data_pagamento", -1).limit(limit)
    saida = []
    for doc in cursor:
        _enriquecer_titulo(doc)
        saida.append(doc)
    return saida


def obter_titulo_por_id(titulo_id: str) -> Optional[Dict[str, Any]]:
    """Retorna um título por id."""
    coll = get_titulos_collection()
    try:
        doc = coll.find_one({"_id": ObjectId(titulo_id)})
    except Exception:
        return None
    if not doc:
        return None
    _enriquecer_titulo(doc)
    return doc


def registrar_pagamento(titulo_id: str, data_pagamento=None) -> Optional[Dict[str, Any]]:
    """
    Marca o título como PAGO e registra a data de pagamento.
    data_pagamento: datetime ou str YYYY-MM-DD; se None, usa hoje.
    """
    coll = get_titulos_collection()
    try:
        oid = ObjectId(titulo_id)
    except Exception:
        return None
    doc = coll.find_one({"_id": oid, "status": "PENDENTE"})
    if not doc:
        return None
    if data_pagamento:
        if hasattr(data_pagamento, "strftime"):
            data_pag_dt = data_pagamento
        else:
            try:
                data_pag_dt = datetime.strptime(str(data_pagamento)[:10], "%Y-%m-%d")
            except Exception:
                data_pag_dt = datetime.utcnow()
    else:
        data_pag_dt = datetime.utcnow()
    coll.update_one(
        {"_id": oid},
        {"$set": {"status": "PAGO", "data_pagamento": data_pag_dt}},
    )
    return obter_titulo_por_id(titulo_id)


def despesas_titulos_hoje() -> float:
    """Soma dos valores de títulos PAGO com data_pagamento = hoje (para dashboard)."""
    db = get_database()
    coll = db["financeiro_titulos"]
    hoje = datetime.utcnow().date()
    inicio = datetime(hoje.year, hoje.month, hoje.day, 0, 0, 0, 0)
    fim = datetime(hoje.year, hoje.month, hoje.day, 23, 59, 59, 999000)
    res = list(coll.aggregate([
        {"$match": {"status": "PAGO", "data_pagamento": {"$gte": inicio, "$lte": fim}}},
        {"$group": {"_id": None, "total": {"$sum": "$valor"}}},
    ]))
    if not res:
        return 0.0
    return round(float(res[0].get("total", 0)), 2)


def despesas_titulos_por_dia(inicio: datetime, fim: datetime) -> Dict[int, float]:
    """Retorna {dia: total} para títulos PAGO no intervalo (dia = day of month)."""
    from calendar import monthrange
    db = get_database()
    coll = db["financeiro_titulos"]
    res = list(coll.aggregate([
        {"$match": {"status": "PAGO", "data_pagamento": {"$gte": inicio, "$lte": fim}}},
        {"$group": {"_id": {"$dayOfMonth": "$data_pagamento"}, "total": {"$sum": "$valor"}}},
    ]))
    return {r["_id"]: float(r["total"]) for r in res}


def despesas_titulos_por_mes(inicio: datetime, fim: datetime) -> List[Dict[str, Any]]:
    """Retorna lista [{data: "mm/yyyy", valor: float}] para títulos PAGO no intervalo."""
    db = get_database()
    coll = db["financeiro_titulos"]
    res = list(coll.aggregate([
        {"$match": {"status": "PAGO", "data_pagamento": {"$gte": inicio, "$lte": fim}}},
        {"$group": {"_id": {"year": {"$year": "$data_pagamento"}, "month": {"$month": "$data_pagamento"}}, "total": {"$sum": "$valor"}}},
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]))
    return [{"data": f"{r['_id']['month']:02d}/{r['_id']['year']}", "valor": round(float(r["total"]), 2)} for r in res]


def grafico_despesas_titulos_mes() -> List[Dict[str, Any]]:
    """Despesas por dia no mês atual (títulos PAGO). Formato [{\"data\": \"dd/mm\", \"valor\": float}, ...]."""
    from calendar import monthrange
    now = datetime.utcnow()
    inicio = datetime(now.year, now.month, 1, 0, 0, 0, 0)
    if now.month == 12:
        fim = datetime(now.year, 12, 31, 23, 59, 59, 999000)
    else:
        fim = datetime(now.year, now.month + 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
    _, ultimo = monthrange(inicio.year, inicio.month)
    por_dia = despesas_titulos_por_dia(inicio, fim)
    return [{"data": f"{d:02d}/{inicio.month:02d}", "valor": round(por_dia.get(d, 0), 2)} for d in range(1, ultimo + 1)]


def grafico_despesas_titulos_3meses() -> List[Dict[str, Any]]:
    """Despesas por mês (últimos 3 meses) de títulos PAGO. Formato [{\"data\": \"mm/yyyy\", \"valor\": float}, ...]."""
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
        res = list(get_database()["financeiro_titulos"].aggregate([
            {"$match": {"status": "PAGO", "data_pagamento": {"$gte": di, "$lte": df}}},
            {"$group": {"_id": None, "total": {"$sum": "$valor"}}},
        ]))
        total = float(res[0]["total"]) if res and res[0].get("total") else 0.0
        saida.append({"data": f"{m:02d}/{y}", "valor": round(total, 2)})
    return saida


def alertas_titulos_pendentes() -> Dict[str, List[Dict[str, Any]]]:
    """
    Títulos PENDENTE agrupados por semana (esta_semana, semana_que_vem, proxima_semana).
    Usa data_vencimento quando existir; sem vencimento vai para esta_semana.
    """
    from datetime import timedelta
    db = get_database()
    coll = db["financeiro_titulos"]
    fornecedores = db["fornecedores"]
    entradas = db["entradas_estoque"]
    hoje = datetime.utcnow().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    inicio_proxima = fim_semana + timedelta(days=1)
    fim_proxima = inicio_proxima + timedelta(days=6)
    inicio_seguinte = fim_proxima + timedelta(days=1)
    fim_seguinte = inicio_seguinte + timedelta(days=6)

    def em_intervalo(data_val, i_inicio, i_fim):
        if not data_val:
            return False
        d = data_val.date() if hasattr(data_val, "date") else data_val
        return i_inicio <= d <= i_fim

    esta_semana = []
    semana_que_vem = []
    proxima_semana = []

    for doc in coll.find({"status": "PENDENTE"}).sort("data_vencimento", 1):
        doc["id"] = str(doc["_id"])
        valor = float(doc.get("valor", 0))
        entrada_id = doc.get("entrada_id")
        nome_fornecedor = ""
        nf_numero = ""
        if entrada_id:
            eid = ObjectId(entrada_id) if isinstance(entrada_id, str) else entrada_id
            ent = entradas.find_one({"_id": eid})
            if ent:
                f = fornecedores.find_one({"_id": ent.get("fornecedor_id")}) if ent.get("fornecedor_id") else None
                nome_fornecedor = f.get("nome", "") if f else ""
                nf_numero = (ent.get("nf_e") or {}).get("numero", "")
        dv = doc.get("data_vencimento")
        data_fmt = dv.strftime("%d/%m/%Y") if dv and hasattr(dv, "strftime") else "—"
        item = {"id": doc["id"], "data_fmt": data_fmt, "valor": valor, "fornecedor": nome_fornecedor, "nf_numero": nf_numero}
        if dv is None or em_intervalo(dv, inicio_semana, fim_semana):
            esta_semana.append(item)
        elif em_intervalo(dv, inicio_proxima, fim_proxima):
            semana_que_vem.append(item)
        elif em_intervalo(dv, inicio_seguinte, fim_seguinte):
            proxima_semana.append(item)

    return {"esta_semana": esta_semana, "semana_que_vem": semana_que_vem, "proxima_semana": proxima_semana}
