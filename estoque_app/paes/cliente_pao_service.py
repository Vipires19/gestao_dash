"""
Service para ClientePao (módulo PÃES).
Acesso direto ao MongoDB via pymongo.
Collection: clientes_pao
Documento: nome, telefone, endereco, observacoes (opcional), ativo, created_at, updated_at
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database


def get_clientes_pao_collection():
    """Retorna a collection clientes_pao."""
    return get_database()["clientes_pao"]


def listar_clientes_ativos() -> List[Dict[str, Any]]:
    """Lista apenas clientes ativos, ordenados por nome. Normaliza _id para id."""
    coll = get_clientes_pao_collection()
    cursor = coll.find({"ativo": True}).sort("nome", 1)
    saida = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        saida.append(doc)
    return saida


def obter_por_id(cliente_id: str) -> Optional[Dict[str, Any]]:
    """Retorna um cliente por id ou None. Normaliza _id para id."""
    coll = get_clientes_pao_collection()
    try:
        doc = coll.find_one({"_id": ObjectId(cliente_id)})
    except Exception:
        return None
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    return doc


def criar(nome: str, telefone: str, endereco: str, observacoes: str = "") -> Dict[str, Any]:
    """Cria um cliente. Retorna o documento com id (string)."""
    nome = (nome or "").strip()
    telefone = (telefone or "").strip()
    endereco = (endereco or "").strip()
    if not nome:
        raise ValueError("Nome é obrigatório.")
    if not telefone:
        raise ValueError("Telefone é obrigatório.")
    if not endereco:
        raise ValueError("Endereço é obrigatório.")
    now = datetime.utcnow()
    doc = {
        "nome": nome,
        "telefone": telefone,
        "endereco": endereco,
        "observacoes": (observacoes or "").strip(),
        "ativo": True,
        "created_at": now,
        "updated_at": now,
    }
    coll = get_clientes_pao_collection()
    result = coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(doc["_id"])
    return doc


def atualizar(
    cliente_id: str,
    nome: str,
    telefone: str,
    endereco: str,
    observacoes: str = "",
    created_at: datetime = None,
) -> Optional[Dict[str, Any]]:
    """Atualiza um cliente. Mantém created_at, atualiza updated_at. Retorna o documento ou None."""
    coll = get_clientes_pao_collection()
    try:
        oid = ObjectId(cliente_id)
    except Exception:
        return None
    doc = coll.find_one({"_id": oid})
    if not doc:
        return None
    nome = (nome or "").strip()
    telefone = (telefone or "").strip()
    endereco = (endereco or "").strip()
    if not nome:
        raise ValueError("Nome é obrigatório.")
    if not telefone:
        raise ValueError("Telefone é obrigatório.")
    if not endereco:
        raise ValueError("Endereço é obrigatório.")
    now = datetime.utcnow()
    update = {
        "nome": nome,
        "telefone": telefone,
        "endereco": endereco,
        "observacoes": (observacoes or "").strip(),
        "updated_at": now,
    }
    if created_at is not None:
        update["created_at"] = created_at
    coll.update_one({"_id": oid}, {"$set": update})
    return obter_por_id(cliente_id)


def inativar(cliente_id: str) -> bool:
    """Soft delete: define ativo = False. Retorna True se encontrou e atualizou."""
    coll = get_clientes_pao_collection()
    try:
        oid = ObjectId(cliente_id)
    except Exception:
        return False
    result = coll.update_one(
        {"_id": oid},
        {"$set": {"ativo": False, "updated_at": datetime.utcnow()}},
    )
    return result.modified_count == 1
