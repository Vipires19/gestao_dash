"""
Service para fornecedores (operação / entradas de estoque).
Acesso direto ao MongoDB via pymongo (sem ORM).
"""
from datetime import datetime
from typing import List, Dict, Any
from core.database import get_database


def get_fornecedores_collection():
    """Retorna a collection de fornecedores."""
    return get_database()["fornecedores"]


def listar_fornecedores() -> List[Dict[str, Any]]:
    """Lista todos os fornecedores ordenados por nome. Normaliza _id para id."""
    coll = get_fornecedores_collection()
    cursor = coll.find().sort("nome", 1)
    saida = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        saida.append(doc)
    return saida


def criar_fornecedor(nome: str) -> Dict[str, Any]:
    """Cria um fornecedor. Retorna o documento com id (string)."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Nome do fornecedor é obrigatório.")
    coll = get_fornecedores_collection()
    now = datetime.utcnow()
    doc = {"nome": nome, "created_at": now}
    result = coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(doc["_id"])
    return doc


def obter_fornecedor_por_id(fornecedor_id: str):
    """Retorna o fornecedor pelo id ou None. Normaliza _id para id."""
    from bson import ObjectId
    coll = get_fornecedores_collection()
    try:
        doc = coll.find_one({"_id": ObjectId(fornecedor_id)})
    except Exception:
        return None
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    return doc
