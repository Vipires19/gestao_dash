"""
Service para processamentos / corte (Fase 2).
Collection: processamentos. Atualiza caixas_estoque (peso e status).
Acesso direto ao MongoDB via pymongo (sem ORM).
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database

from estoque_app.services.caixa_estoque_service import get_caixas_collection


def get_processamentos_collection():
    """Retorna a collection de processamentos."""
    return get_database()["processamentos"]


def listar_processamentos() -> List[Dict[str, Any]]:
    """
    Lista processamentos ordenados por data_processamento desc.
    Normaliza _id para id; formata data para exibição.
    """
    coll = get_processamentos_collection()
    cursor = coll.find().sort("data_processamento", -1)
    saida = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        dp = doc.get("data_processamento")
        doc["data_processamento_fmt"] = (
            dp.strftime("%d/%m/%Y") if dp and hasattr(dp, "strftime") else ""
        )
        # Resumo produto base (primeiro da lista ou concatenado)
        caixas_origem = doc.get("caixas_origem") or []
        produtos_base = list({c.get("produto_base", "") for c in caixas_origem if c.get("produto_base")})
        doc["produto_base_resumo"] = ", ".join(produtos_base) if produtos_base else "—"
        doc["qtd_caixas_utilizadas"] = len(caixas_origem)
        saida.append(doc)
    return saida


def criar_processamento(
    data_processamento,
    caixas_origem: List[Dict[str, Any]],
    produtos_gerados: List[Dict[str, Any]],
    perda_kg: float,
    observacoes: str = "",
) -> Dict[str, Any]:
    """
    Cria documento em processamentos e atualiza caixas_estoque.
    caixas_origem: lista de { caixa_id, produto_base, peso_utilizado_kg }
    produtos_gerados: lista de { produto, peso_kg }
    Regra: peso_total_origem = soma(produtos_gerados.peso_kg) + perda_kg
    """
    if not caixas_origem:
        raise ValueError("Selecione ao menos uma caixa de origem.")
    if not produtos_gerados:
        raise ValueError("Informe ao menos um produto gerado.")

    peso_total_origem = sum(c.get("peso_utilizado_kg") or 0 for c in caixas_origem)
    peso_aproveitado = sum(p.get("peso_kg") or 0 for p in produtos_gerados)
    if perda_kg is None:
        perda_kg = 0.0
    perda_kg = round(float(perda_kg), 3)

    # Validação obrigatória: origem = aproveitado + perda
    if abs(peso_total_origem - (peso_aproveitado + perda_kg)) > 0.001:
        raise ValueError(
            f"Peso total de origem ({peso_total_origem:.2f} kg) deve ser igual à "
            f"soma dos produtos gerados ({peso_aproveitado:.2f} kg) + perda ({perda_kg:.2f} kg)."
        )

    percentual_perda = round((perda_kg / peso_total_origem * 100), 2) if peso_total_origem else 0

    caixas_coll = get_caixas_collection()
    caixas_doc = []
    for item in caixas_origem:
        caixa_id = item.get("caixa_id")
        peso_utilizado = float(item.get("peso_utilizado_kg") or 0)
        produto_base = (item.get("produto_base") or "").strip()
        if not caixa_id or peso_utilizado <= 0:
            continue
        try:
            oid = ObjectId(caixa_id)
        except Exception:
            raise ValueError(f"ID de caixa inválido: {caixa_id}")
        caixa = caixas_coll.find_one({"_id": oid})
        if not caixa:
            raise ValueError(f"Caixa não encontrada: {caixa_id}")
        if caixa.get("status") != "EM_ESTOQUE":
            raise ValueError(f"Caixa {caixa_id} não está disponível para processamento.")
        peso_atual = float(caixa.get("peso_atual_kg") or 0)
        if peso_atual <= 0:
            raise ValueError(f"Caixa {caixa_id} não possui peso disponível.")
        if peso_utilizado > peso_atual:
            raise ValueError(
                f"Peso utilizado ({peso_utilizado} kg) não pode exceder o peso atual da caixa ({peso_atual} kg)."
            )
        caixas_doc.append({
            "caixa_id": oid,
            "produto_base": produto_base or caixa.get("produto_base", ""),
            "peso_utilizado_kg": round(peso_utilizado, 3),
        })

    if not caixas_doc:
        raise ValueError("Nenhuma caixa válida para processamento.")

    # Recalcula peso_total_origem a partir das caixas validadas
    peso_total_origem = sum(c["peso_utilizado_kg"] for c in caixas_doc)
    if abs(peso_total_origem - (peso_aproveitado + perda_kg)) > 0.001:
        raise ValueError(
            f"Peso total de origem ({peso_total_origem:.2f} kg) deve ser igual à "
            f"soma dos produtos gerados ({peso_aproveitado:.2f} kg) + perda ({perda_kg:.2f} kg)."
        )

    now = datetime.utcnow()
    if hasattr(data_processamento, "strftime"):
        data_processamento_dt = data_processamento
    else:
        try:
            data_processamento_dt = datetime.strptime(str(data_processamento)[:10], "%Y-%m-%d")
        except Exception:
            raise ValueError("Data do processamento inválida.")

    processamento_doc = {
        "data_processamento": data_processamento_dt,
        "caixas_origem": [
            {
                "caixa_id": str(c["caixa_id"]),
                "produto_base": c["produto_base"],
                "peso_utilizado_kg": c["peso_utilizado_kg"],
            }
            for c in caixas_doc
        ],
        "peso_total_origem": round(peso_total_origem, 3),
        "produtos_gerados": [
            {"produto": (p.get("produto") or "").strip(), "peso_kg": round(float(p.get("peso_kg") or 0), 3)}
            for p in produtos_gerados
            if (p.get("produto") or "").strip()
        ],
        "perda": {
            "peso_kg": round(perda_kg, 3),
            "percentual": round(percentual_perda, 2),
        },
        "observacoes": (observacoes or "").strip(),
        "created_at": now,
    }

    proc_coll = get_processamentos_collection()
    result = proc_coll.insert_one(processamento_doc)
    processamento_doc["_id"] = result.inserted_id
    processamento_doc["id"] = str(result.inserted_id)

    # Atualizar caixas: subtrair peso e atualizar status
    for c in caixas_doc:
        caixa_id = c["caixa_id"]
        peso_utilizado = c["peso_utilizado_kg"]
        caixa = caixas_coll.find_one({"_id": caixa_id})
        if not caixa:
            continue
        novo_peso = round(float(caixa.get("peso_atual_kg") or 0) - peso_utilizado, 3)
        novo_status = "FINALIZADA" if novo_peso <= 0 else "EM_ESTOQUE"
        caixas_coll.update_one(
            {"_id": caixa_id},
            {"$set": {"peso_atual_kg": max(0, novo_peso), "status": novo_status}},
        )

    return processamento_doc
