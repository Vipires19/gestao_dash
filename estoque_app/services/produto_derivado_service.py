"""
Service para produtos derivados (Fase 3).
Collection: produtos_derivados.
Criados a partir de processamentos; atualizados ao vender.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database

from estoque_app.services.caixa_estoque_service import get_caixas_collection


def get_produtos_derivados_collection():
    """Retorna a collection produtos_derivados."""
    return get_database()["produtos_derivados"]


def registrar_from_processamento(processamento_doc: Dict[str, Any]) -> None:
    """
    Cria documentos em produtos_derivados a partir de um processamento.
    Calcula custo total de origem pelas caixas (peso_utilizado * valor_kg)
    e distribui por peso entre os produtos gerados.
    """
    caixas_origem = processamento_doc.get("caixas_origem") or []
    produtos_gerados = processamento_doc.get("produtos_gerados") or []
    peso_total_origem = float(processamento_doc.get("peso_total_origem") or 0)
    processamento_id = processamento_doc.get("_id") or processamento_doc.get("id")
    if isinstance(processamento_id, str):
        processamento_id = ObjectId(processamento_id)

    if not produtos_gerados or peso_total_origem <= 0:
        return

    caixas_coll = get_caixas_collection()
    custo_total_origem = 0.0
    for c in caixas_origem:
        caixa_id = c.get("caixa_id")
        if isinstance(caixa_id, str):
            try:
                caixa_id = ObjectId(caixa_id)
            except Exception:
                continue
        caixa = caixas_coll.find_one({"_id": caixa_id})
        if not caixa:
            continue
        peso_utilizado = float(c.get("peso_utilizado_kg") or 0)
        valor_kg = float(caixa.get("valor_kg") or 0)
        custo_total_origem += peso_utilizado * valor_kg

    coll = get_produtos_derivados_collection()
    now = datetime.utcnow()
    for p in produtos_gerados:
        produto_nome = (p.get("produto") or "").strip()
        peso_kg = float(p.get("peso_kg") or 0)
        if not produto_nome or peso_kg <= 0:
            continue
        proporcao = peso_kg / peso_total_origem if peso_total_origem else 0
        custo_total = round(custo_total_origem * proporcao, 2)
        custo_kg = round(custo_total / peso_kg, 2) if peso_kg else 0
        doc = {
            "produto": produto_nome,
            "peso_disponivel_kg": round(peso_kg, 3),
            "custo_total": custo_total,
            "custo_kg": custo_kg,
            "origem_processamento_id": processamento_id,
            "created_at": now,
        }
        if p.get("divisao_lucro"):
            doc["divisao_lucro"] = {
                "cliente_percentual": int(p["divisao_lucro"].get("cliente_percentual", 70)),
                "socio_percentual": int(p["divisao_lucro"].get("socio_percentual", 30)),
            }
        coll.insert_one(doc)


def listar_disponiveis(produto: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lista produtos derivados com peso_disponivel_kg > 0. Ordena por produto e created_at."""
    coll = get_produtos_derivados_collection()
    match = {"peso_disponivel_kg": {"$gt": 0}}
    if produto and produto.strip():
        match["produto"] = {"$regex": produto.strip(), "$options": "i"}
    cursor = coll.find(match).sort([("produto", 1), ("created_at", -1)])
    saida = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc["origem_processamento_id"] = str(doc.get("origem_processamento_id", ""))
        saida.append(doc)
    return saida


def obter_por_id(produto_derivado_id: str) -> Optional[Dict[str, Any]]:
    """Retorna um produto derivado pelo id."""
    coll = get_produtos_derivados_collection()
    try:
        doc = coll.find_one({"_id": ObjectId(produto_derivado_id)})
    except Exception:
        return None
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    doc["origem_processamento_id"] = str(doc.get("origem_processamento_id", ""))
    return doc


def reduzir_peso(produto_derivado_id: str, peso_kg: float) -> None:
    """Subtrai peso_disponivel_kg do produto derivado. Não permite ficar negativo."""
    coll = get_produtos_derivados_collection()
    try:
        oid = ObjectId(produto_derivado_id)
    except Exception:
        raise ValueError("ID de produto derivado inválido.")
    doc = coll.find_one({"_id": oid})
    if not doc:
        raise ValueError("Produto derivado não encontrado.")
    atual = float(doc.get("peso_disponivel_kg") or 0)
    if peso_kg > atual:
        raise ValueError(f"Peso a vender ({peso_kg} kg) excede o disponível ({atual} kg).")
    novo = round(atual - peso_kg, 3)
    coll.update_one({"_id": oid}, {"$set": {"peso_disponivel_kg": max(0, novo)}})
