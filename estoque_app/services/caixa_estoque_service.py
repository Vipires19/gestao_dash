"""
Service para caixas em estoque (operação).
Acesso direto ao MongoDB via pymongo (sem ORM).
"""
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo import ReturnDocument
from core.database import get_database


def get_caixas_collection():
    """Retorna a collection de caixas_estoque."""
    return get_database()["caixas_estoque"]


def get_proximo_codigo_caixa() -> str:
    """
    Gera o próximo código único de caixa (ex: CX-0001, CX-0002).
    Usa a collection contadores para sequência atômica.
    """
    db = get_database()
    coll = db["contadores"]
    result = coll.find_one_and_update(
        {"_id": "caixa_codigo"},
        {"$inc": {"ultimo": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    ultimo = result.get("ultimo", 1)
    return "CX-" + str(ultimo).zfill(4)


def listar_caixas(
    produto: Optional[str] = None,
    fornecedor_id: Optional[str] = None,
    status: Optional[str] = None,
    codigo: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Lista caixas com filtros opcionais. Ordena por created_at desc.
    Normaliza _id para id; adiciona data_entrada e nome_fornecedor quando possível.
    codigo: filtra por codigo_caixa (regex case-insensitive).
    """
    coll = get_caixas_collection()
    match = {}
    if produto and produto.strip():
        match["produto_base"] = {"$regex": produto.strip(), "$options": "i"}
    if codigo and codigo.strip():
        match["codigo_caixa"] = {"$regex": codigo.strip(), "$options": "i"}
    if fornecedor_id and fornecedor_id.strip():
        try:
            match["fornecedor_id"] = ObjectId(fornecedor_id.strip())
        except Exception:
            pass
    if status and status.strip():
        match["status"] = status.strip()
    cursor = coll.find(match).sort("created_at", -1)
    saida = []
    db = get_database()
    fornecedores = db["fornecedores"]
    entradas = db["entradas_estoque"]
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        if not doc.get("codigo_caixa"):
            codigo = get_proximo_codigo_caixa()
            coll.update_one({"_id": doc["_id"]}, {"$set": {"codigo_caixa": codigo}})
            doc["codigo_caixa"] = codigo
        eid = doc.get("entrada_id")
        fid = doc.get("fornecedor_id")
        entrada = entradas.find_one({"_id": eid}) if eid else None
        if entrada:
            doc["data_entrada"] = entrada.get("data_entrada")
            doc["nf_numero"] = (entrada.get("nf_e") or {}).get("numero")
        else:
            doc["data_entrada"] = None
            doc["nf_numero"] = None
        f = fornecedores.find_one({"_id": fid}) if fid else None
        doc["nome_fornecedor"] = f.get("nome", "") if f else ""
        doc["entrada_id"] = str(eid) if eid else None
        doc["fornecedor_id"] = str(fid) if fid else None
        if doc.get("data_entrada") and hasattr(doc["data_entrada"], "strftime"):
            doc["data_entrada_fmt"] = doc["data_entrada"].strftime("%d/%m/%Y")
        else:
            doc["data_entrada_fmt"] = ""
        saida.append(doc)
    return saida


def obter_caixa_por_id(caixa_id: str) -> Optional[Dict[str, Any]]:
    """Retorna uma caixa pelo id. Normaliza _id; enriquece com entrada e fornecedor."""
    coll = get_caixas_collection()
    try:
        doc = coll.find_one({"_id": ObjectId(caixa_id)})
    except Exception:
        return None
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    if not doc.get("codigo_caixa"):
        codigo = get_proximo_codigo_caixa()
        coll.update_one({"_id": doc["_id"]}, {"$set": {"codigo_caixa": codigo}})
        doc["codigo_caixa"] = codigo
    doc["fornecedor_id"] = str(doc["fornecedor_id"]) if doc.get("fornecedor_id") else None
    doc["entrada_id"] = str(doc["entrada_id"]) if doc.get("entrada_id") else None
    db = get_database()
    entrada = db["entradas_estoque"].find_one({"_id": ObjectId(doc["entrada_id"])}) if doc.get("entrada_id") else None
    if entrada:
        doc["entrada"] = entrada
        doc["entrada"]["id"] = str(entrada["_id"])
        doc["nf_numero"] = (entrada.get("nf_e") or {}).get("numero")
        doc["nf_arquivo"] = (entrada.get("nf_e") or {}).get("arquivo")
    else:
        doc["entrada"] = None
        doc["nf_numero"] = None
        doc["nf_arquivo"] = None
    f = db["fornecedores"].find_one({"_id": ObjectId(doc["fornecedor_id"])}) if doc.get("fornecedor_id") else None
    doc["nome_fornecedor"] = f.get("nome", "") if f else ""
    return doc


def obter_caixa_por_codigo(codigo_caixa: str, apenas_em_estoque: bool = True) -> Optional[Dict[str, Any]]:
    """Retorna uma caixa pelo codigo_caixa. Se apenas_em_estoque=True, só retorna se status=EM_ESTOQUE."""
    import re
    if not codigo_caixa or not str(codigo_caixa).strip():
        return None
    codigo = str(codigo_caixa).strip()
    coll = get_caixas_collection()
    match = {"codigo_caixa": {"$regex": "^" + re.escape(codigo) + "$", "$options": "i"}}
    if apenas_em_estoque:
        match["status"] = "EM_ESTOQUE"
    doc = coll.find_one(match)
    if not doc:
        return None
    return obter_caixa_por_id(str(doc["_id"]))


def count_caixas_por_entrada(entrada_id) -> int:
    """Conta quantas caixas pertencem a uma entrada (entrada_id pode ser ObjectId ou str)."""
    coll = get_caixas_collection()
    if isinstance(entrada_id, str):
        try:
            entrada_id = ObjectId(entrada_id)
        except Exception:
            return 0
    return coll.count_documents({"entrada_id": entrada_id})
