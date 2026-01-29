"""
Service para lógica de despesas operacionais.

Localização: estoque_app/services/despesa_service.py

Acesso direto ao MongoDB via pymongo (sem ORM).
"""
from datetime import datetime
from typing import List, Dict, Any
from core.database import get_database


def get_despesas_collection():
    """
    Retorna a collection de despesas do MongoDB.
    """
    db = get_database()
    return db["despesas"]


def listar_despesas() -> List[Dict[str, Any]]:
    """
    Retorna todas as despesas ordenadas da mais recente para a mais antiga (por data).
    Converte _id para id (string) antes de enviar ao template.
    """
    coll = get_despesas_collection()
    cursor = coll.find().sort("data", -1)
    saida = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        # Formata data para exibição (DD/MM/YYYY)
        d = doc.get("data")
        if d:
            doc["data_formatada"] = d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)
        else:
            doc["data_formatada"] = ""
        saida.append(doc)
    return saida


def criar_despesa(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insere uma nova despesa no MongoDB.

    Args:
        dados: dict com descricao (str), categoria (str), valor (float), data (str YYYY-MM-DD)

    Returns:
        Dict da despesa criada com id (string).

    Raises:
        ValueError: se descricao vazia, valor <= 0 ou data inválida.
    """
    descricao = (dados.get("descricao") or "").strip()
    if not descricao:
        raise ValueError("Descrição é obrigatória")

    try:
        valor = float(dados.get("valor", 0))
    except (TypeError, ValueError):
        raise ValueError("Valor inválido")
    if valor <= 0:
        raise ValueError("Valor deve ser maior que zero")

    data_str = (dados.get("data") or "").strip()
    if not data_str:
        raise ValueError("Data é obrigatória")
    try:
        # Formato do input date: YYYY-MM-DD
        data_dt = datetime.strptime(data_str, "%Y-%m-%d")
        # Armazena apenas a data (meia-noite UTC)
        data_dt = data_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        raise ValueError("Data inválida")

    categoria = (dados.get("categoria") or "").strip()

    now = datetime.utcnow()
    doc = {
        "descricao": descricao,
        "categoria": categoria,
        "valor": round(valor, 2),
        "data": data_dt,
        "created_at": now,
    }
    coll = get_despesas_collection()
    result = coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(doc["_id"])
    doc["data_formatada"] = data_dt.strftime("%d/%m/%Y")
    return doc
