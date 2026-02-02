"""
Service para PlanoEntregaPao (módulo PÃES).
Acesso direto ao MongoDB via pymongo.
Collection: planos_entrega_pao
Documento: cliente_id, tipo_plano, dias_entrega, horario_entrega, quantidade_paes_por_dia,
           valor_por_pao, valor_total_plano, data_pagamento, status_pagamento, status, created_at, updated_at
"""
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database

from estoque_app.paes.cliente_pao_service import get_clientes_pao_collection

TIPO_PLANO_CHOICES = ("DIARIO", "SEMANAL", "MENSAL")
DIAS_SEMANA = ("SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM")
STATUS_PLANO_CHOICES = ("ATIVO", "EM_ATRASO", "CANCELADO")
STATUS_PAGAMENTO_CHOICES = ("PENDENTE", "PAGO")


def get_planos_collection():
    """Retorna a collection planos_entrega_pao."""
    return get_database()["planos_entrega_pao"]


def _calcular_valor_total(
    tipo_plano: str,
    dias_entrega: List[str],
    quantidade_paes_por_dia: int,
    valor_por_pao: float,
) -> float:
    """Calcula valor_total_plano conforme tipo e dias."""
    qtd = max(0, int(quantidade_paes_por_dia))
    valor = max(0.0, float(valor_por_pao))
    dias = len(dias_entrega) if dias_entrega else 0
    if tipo_plano == "DIARIO":
        dias_ciclo = 1
    elif tipo_plano == "SEMANAL":
        dias_ciclo = max(1, dias)
    else:  # MENSAL
        dias_ciclo = max(1, dias) * 4  # ~4 semanas
    return round(dias_ciclo * qtd * valor, 2)


def _status_efetivo(doc: Dict[str, Any]) -> str:
    """Retorna status efetivo: CANCELADO > EM_ATRASO (se pendente e vencido) > ATIVO."""
    if doc.get("status") == "CANCELADO":
        return "CANCELADO"
    data_pag = doc.get("data_pagamento")
    hoje = date.today()
    if doc.get("status_pagamento") == "PENDENTE" and data_pag:
        dp = data_pag.date() if hasattr(data_pag, "date") else data_pag
        if dp < hoje:
            return "EM_ATRASO"
    return doc.get("status", "ATIVO")


def _enriquecer_plano(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Adiciona id, nome_cliente, status_efetivo, data_pagamento_fmt."""
    doc["id"] = str(doc["_id"])
    cliente_id = doc.get("cliente_id")
    if cliente_id:
        coll_cli = get_clientes_pao_collection()
        try:
            c = coll_cli.find_one({"_id": ObjectId(cliente_id) if isinstance(cliente_id, str) else cliente_id})
            doc["nome_cliente"] = c.get("nome", "") if c else ""
        except Exception:
            doc["nome_cliente"] = ""
    else:
        doc["nome_cliente"] = ""
    doc["status_efetivo"] = _status_efetivo(doc)
    dp = doc.get("data_pagamento")
    doc["data_pagamento_fmt"] = dp.strftime("%d/%m/%Y") if dp and hasattr(dp, "strftime") else (str(dp)[:10] if dp else "")
    doc["data_pagamento_iso"] = dp.strftime("%Y-%m-%d") if dp and hasattr(dp, "strftime") else (str(dp)[:10] if dp else "")
    return doc


def listar_agrupado_por_tipo() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Lista planos agrupados por tipo_plano (DIARIO, SEMANAL, MENSAL).
    Dentro de cada tipo, agrupa por status_efetivo: ativos, em_atraso, cancelados.
    Retorna: { "DIARIO": { "ativos": [...], "em_atraso": [...], "cancelados": [...] }, ... }
    """
    coll = get_planos_collection()
    hoje = date.today()
    saida = {
        "DIARIO": {"ativos": [], "em_atraso": [], "cancelados": []},
        "SEMANAL": {"ativos": [], "em_atraso": [], "cancelados": []},
        "MENSAL": {"ativos": [], "em_atraso": [], "cancelados": []},
    }
    for doc in coll.find().sort("created_at", -1):
        _enriquecer_plano(doc)
        tipo = doc.get("tipo_plano") or "SEMANAL"
        if tipo not in saida:
            saida[tipo] = {"ativos": [], "em_atraso": [], "cancelados": []}
        se = doc["status_efetivo"]
        if se == "CANCELADO":
            saida[tipo]["cancelados"].append(doc)
        elif se == "EM_ATRASO":
            saida[tipo]["em_atraso"].append(doc)
        else:
            saida[tipo]["ativos"].append(doc)
    return saida


def obter_por_id(plano_id: str) -> Optional[Dict[str, Any]]:
    """Retorna um plano por id ou None. Normaliza _id para id e enriquece."""
    coll = get_planos_collection()
    try:
        doc = coll.find_one({"_id": ObjectId(plano_id)})
    except Exception:
        return None
    if not doc:
        return None
    return _enriquecer_plano(doc)


def criar(
    cliente_id: str,
    tipo_plano: str,
    dias_entrega: List[str],
    horario_entrega: str,
    quantidade_paes_por_dia: int,
    valor_por_pao: float,
    data_pagamento,
) -> Dict[str, Any]:
    """Cria um plano. status=ATIVO, status_pagamento=PENDENTE. Calcula valor_total_plano."""
    tipo_plano = (tipo_plano or "SEMANAL").strip().upper()
    if tipo_plano not in TIPO_PLANO_CHOICES:
        raise ValueError("Tipo de plano inválido.")
    try:
        cid = ObjectId(cliente_id)
    except Exception:
        raise ValueError("Cliente inválido.")
    dias_entrega = [d.strip().upper() for d in (dias_entrega or []) if d and d.strip()]
    horario_entrega = (horario_entrega or "06:00").strip()[:5]
    qtd = max(0, int(quantidade_paes_por_dia))
    valor = max(0.0, float(valor_por_pao))
    if not data_pagamento:
        raise ValueError("Data de pagamento é obrigatória.")
    if hasattr(data_pagamento, "date"):
        data_pag_dt = datetime(data_pagamento.year, data_pagamento.month, data_pagamento.day)
    else:
        try:
            data_pag_dt = datetime.strptime(str(data_pagamento)[:10], "%Y-%m-%d")
        except Exception:
            raise ValueError("Data de pagamento inválida.")
    valor_total = _calcular_valor_total(tipo_plano, dias_entrega, qtd, valor)
    now = datetime.utcnow()
    doc = {
        "cliente_id": cid,
        "tipo_plano": tipo_plano,
        "dias_entrega": dias_entrega,
        "horario_entrega": horario_entrega,
        "quantidade_paes_por_dia": qtd,
        "valor_por_pao": round(valor, 2),
        "valor_total_plano": valor_total,
        "data_pagamento": data_pag_dt,
        "status_pagamento": "PENDENTE",
        "status": "ATIVO",
        "created_at": now,
        "updated_at": now,
    }
    coll = get_planos_collection()
    result = coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(doc["_id"])
    return _enriquecer_plano(doc)


def atualizar(
    plano_id: str,
    dias_entrega: List[str],
    quantidade_paes_por_dia: int,
    valor_por_pao: float,
    data_pagamento,
) -> Optional[Dict[str, Any]]:
    """Atualiza dias, quantidade, valor_por_pao, data_pagamento. Recalcula valor_total_plano."""
    coll = get_planos_collection()
    try:
        oid = ObjectId(plano_id)
    except Exception:
        return None
    doc = coll.find_one({"_id": oid})
    if not doc:
        return None
    dias_entrega = [d.strip().upper() for d in (dias_entrega or []) if d and d.strip()]
    qtd = max(0, int(quantidade_paes_por_dia))
    valor = max(0.0, float(valor_por_pao))
    if not data_pagamento:
        raise ValueError("Data de pagamento é obrigatória.")
    if hasattr(data_pagamento, "date"):
        data_pag_dt = datetime(data_pagamento.year, data_pagamento.month, data_pagamento.day)
    else:
        try:
            data_pag_dt = datetime.strptime(str(data_pagamento)[:10], "%Y-%m-%d")
        except Exception:
            raise ValueError("Data de pagamento inválida.")
    tipo = doc.get("tipo_plano", "SEMANAL")
    valor_total = _calcular_valor_total(tipo, dias_entrega, qtd, valor)
    now = datetime.utcnow()
    coll.update_one(
        {"_id": oid},
        {"$set": {
            "dias_entrega": dias_entrega,
            "quantidade_paes_por_dia": qtd,
            "valor_por_pao": round(valor, 2),
            "valor_total_plano": valor_total,
            "data_pagamento": data_pag_dt,
            "updated_at": now,
        }},
    )
    return obter_por_id(plano_id)


def cancelar(plano_id: str) -> bool:
    """Soft cancel: status = CANCELADO. Retorna True se encontrou e atualizou."""
    coll = get_planos_collection()
    try:
        oid = ObjectId(plano_id)
    except Exception:
        return False
    result = coll.update_one(
        {"_id": oid},
        {"$set": {"status": "CANCELADO", "updated_at": datetime.utcnow()}},
    )
    return result.modified_count == 1
