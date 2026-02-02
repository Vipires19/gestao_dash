"""
Service para entradas de estoque (operação / compras).
Acesso direto ao MongoDB via pymongo (sem ORM).
Cria entradas e gera automaticamente as caixas em caixas_estoque.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database

from estoque_app.services.caixa_estoque_service import get_caixas_collection, get_proximo_codigo_caixa
from estoque_app.services.financeiro_titulo_service import criar_titulo_para_entrada


def get_entradas_collection():
    """Retorna a collection de entradas_estoque."""
    return get_database()["entradas_estoque"]


def listar_entradas() -> List[Dict[str, Any]]:
    """Lista entradas ordenadas por data_entrada desc. Normaliza _id; adiciona nome_fornecedor e qtd_caixas."""
    coll = get_entradas_collection()
    caixas_coll = get_caixas_collection()
    fornecedores = get_database()["fornecedores"]
    cursor = coll.find().sort("data_entrada", -1)
    saida = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        fid = doc.get("fornecedor_id")
        f = fornecedores.find_one({"_id": fid}) if fid else None
        doc["nome_fornecedor"] = f.get("nome", "") if f else ""
        doc["fornecedor_id"] = str(fid) if fid else None
        qtd = caixas_coll.count_documents({"entrada_id": doc["_id"]}) if doc.get("_id") else 0
        doc["qtd_caixas"] = qtd
        # Formatações para template
        de = doc.get("data_entrada")
        doc["data_entrada_fmt"] = de.strftime("%d/%m/%Y") if de and hasattr(de, "strftime") else ""
        fin = (doc.get("financeiro") or {})
        dp = fin.get("data_pagamento")
        doc["data_pagamento_fmt"] = dp.strftime("%d/%m/%Y") if dp and hasattr(dp, "strftime") else ""
        doc["valor_total"] = fin.get("valor_total", 0)
        doc["status_pagamento"] = fin.get("status_pagamento", "")
        nf = doc.get("nf_e") or {}
        doc["nf_numero"] = nf.get("numero", "")
        saida.append(doc)
    return saida


def obter_entrada_por_id(entrada_id: str) -> Optional[Dict[str, Any]]:
    """Retorna uma entrada pelo id. Normaliza _id e fornecedor_id; adiciona nome_fornecedor e qtd_caixas."""
    coll = get_entradas_collection()
    try:
        doc = coll.find_one({"_id": ObjectId(entrada_id)})
    except Exception:
        return None
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    fid = doc.get("fornecedor_id")
    f = get_database()["fornecedores"].find_one({"_id": fid}) if fid else None
    doc["nome_fornecedor"] = f.get("nome", "") if f else ""
    doc["fornecedor_id"] = str(fid) if fid else None
    doc["qtd_caixas"] = get_caixas_collection().count_documents({"entrada_id": doc["_id"]})
    return doc


def criar_entrada(
    fornecedor_id: str,
    data_entrada,
    valor_total: float,
    data_pagamento=None,
    status_pagamento: str = "PENDENTE",
    forma_pagamento: str = "BOLETO",
    parcelas: int = 1,
    nf_numero: str = "",
    nf_arquivo: str = "",
    observacoes: str = "",
    produtos: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Cria documento em entradas_estoque e gera as caixas em caixas_estoque.
    produtos: lista de { produto_base, quantidade_caixas, peso_por_caixa_kg, valor_total_produto }
    Retorna a entrada criada com id.
    """
    produtos = produtos or []
    if not fornecedor_id or not str(fornecedor_id).strip():
        raise ValueError("Fornecedor é obrigatório.")
    try:
        fid = ObjectId(fornecedor_id)
    except Exception:
        raise ValueError("Fornecedor inválido.")
    if not data_entrada:
        raise ValueError("Data da entrada é obrigatória.")
    if valor_total is None or valor_total < 0:
        raise ValueError("Valor total inválido.")
    # Normaliza data_entrada e data_pagamento para datetime
    if hasattr(data_entrada, "strftime"):
        data_entrada_dt = data_entrada
    else:
        try:
            data_entrada_dt = datetime.strptime(str(data_entrada)[:10], "%Y-%m-%d")
        except Exception:
            raise ValueError("Data da entrada inválida.")
    if data_pagamento:
        if hasattr(data_pagamento, "strftime"):
            data_pagamento_dt = data_pagamento
        else:
            try:
                data_pagamento_dt = datetime.strptime(str(data_pagamento)[:10], "%Y-%m-%d")
            except Exception:
                data_pagamento_dt = None
    else:
        data_pagamento_dt = None
    now = datetime.utcnow()
    entrada_doc = {
        "fornecedor_id": fid,
        "tipo_entrada": "COMPRA_CARNE",
        "data_entrada": data_entrada_dt,
        "financeiro": {
            "valor_total": round(float(valor_total), 2),
            "data_pagamento": data_pagamento_dt,
            "status_pagamento": (status_pagamento or "PENDENTE").strip(),
            "forma_pagamento": (forma_pagamento or "BOLETO").strip(),
            "parcelas": int(parcelas) if parcelas else 1,
        },
        "nf_e": {
            "numero": (nf_numero or "").strip(),
            "arquivo": (nf_arquivo or "").strip(),
        },
        "observacoes": (observacoes or "").strip(),
        "created_at": now,
    }
    entradas_coll = get_entradas_collection()
    result = entradas_coll.insert_one(entrada_doc)
    entrada_id = result.inserted_id
    # Criar título financeiro PENDENTE (obrigação gerada pela entrada)
    try:
        data_venc = data_pagamento_dt if data_pagamento_dt and (status_pagamento or "").strip() == "PENDENTE" else None
        criar_titulo_para_entrada(entrada_id=entrada_id, valor=round(float(valor_total), 2), data_vencimento=data_venc)
    except Exception:
        pass
    caixas_coll = get_caixas_collection()
    for item in produtos:
        produto_base = (item.get("produto_base") or "").strip()
        qtd_caixas = int(item.get("quantidade_caixas") or 0)
        peso_por_caixa = float(item.get("peso_por_caixa_kg") or 0)
        valor_total_produto = float(item.get("valor_total_produto") or 0)
        if qtd_caixas <= 0 or peso_por_caixa <= 0:
            continue
        valor_por_caixa = valor_total_produto / qtd_caixas if qtd_caixas else 0
        valor_kg = valor_por_caixa / peso_por_caixa if peso_por_caixa else 0
        for _ in range(qtd_caixas):
            caixa_doc = {
                "entrada_id": entrada_id,
                "fornecedor_id": fid,
                "produto_base": produto_base,
                "codigo_caixa": get_proximo_codigo_caixa(),
                "peso_inicial_kg": round(peso_por_caixa, 3),
                "peso_atual_kg": round(peso_por_caixa, 3),
                "valor_total_caixa": round(valor_por_caixa, 2),
                "valor_kg": round(valor_kg, 2),
                "status": "EM_ESTOQUE",
                "created_at": now,
            }
            caixas_coll.insert_one(caixa_doc)
    entrada_doc["_id"] = entrada_id
    entrada_doc["id"] = str(entrada_id)
    return entrada_doc
