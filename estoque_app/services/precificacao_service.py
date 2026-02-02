"""
Service para precificação de produtos comerciais (Emporium Prime).
Produto comercial = produto_base + tipo (CAIXA | PROCESSADO) + nome_comercial.
Itens de estoque herdam o preço do produto comercial.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database


def get_precificacao_collection():
    """Retorna a collection precificacao_emporium."""
    return get_database()["precificacao_emporium"]


def listar_produtos_base_caixa() -> List[str]:
    """Distinct produto_base de caixas_estoque (EM_ESTOQUE). Ordenado."""
    db = get_database()
    coll = db["caixas_estoque"]
    cursor = coll.distinct("produto_base", {"status": "EM_ESTOQUE"})
    return sorted([p for p in cursor if p and str(p).strip()], key=lambda x: x.upper())


def listar_produtos_base_processado() -> List[str]:
    """Distinct produto de produtos_derivados com peso > 0. Ordenado."""
    db = get_database()
    coll = db["produtos_derivados"]
    cursor = coll.distinct("produto", {"peso_disponivel_kg": {"$gt": 0}})
    return sorted([p for p in cursor if p and str(p).strip()], key=lambda x: x.upper())


def _perda_media_caixa(produto_base: str) -> float:
    """Perda média histórica (%) de processamentos que usaram caixas com este produto_base."""
    db = get_database()
    proc = db["processamentos"]
    percentuais = []
    for doc in proc.find({"caixas_origem": {"$elemMatch": {"produto_base": produto_base}}}):
        perda = doc.get("perda") or {}
        pct = perda.get("percentual")
        if pct is not None:
            percentuais.append(float(pct))
    if not percentuais:
        return 0.0
    return round(sum(percentuais) / len(percentuais), 2)


def _perda_media_processado(produto_nome: str) -> float:
    """Perda média histórica (%) de processamentos que geraram derivados com este produto."""
    db = get_database()
    derivados = db["produtos_derivados"]
    proc = db["processamentos"]
    proc_ids = set()
    for doc in derivados.find({"produto": produto_nome}):
        oid = doc.get("origem_processamento_id")
        if oid:
            proc_ids.add(str(oid) if not isinstance(oid, str) else oid)
    percentuais = []
    for pid in proc_ids:
        try:
            doc = proc.find_one({"_id": ObjectId(pid)})
            if doc:
                perda = doc.get("perda") or {}
                pct = perda.get("percentual")
                if pct is not None:
                    percentuais.append(float(pct))
        except Exception:
            pass
    if not percentuais:
        return 0.0
    return round(sum(percentuais) / len(percentuais), 2)


def analise_estoque(produto_base: str, tipo: str) -> Dict[str, Any]:
    """
    Agrupa itens de estoque correspondentes e calcula:
    custo_medio_ponderado_kg, perda_media_percentual, custo_real_kg, quantidade_estoque_kg.
    tipo: CAIXA | PROCESSADO.
    """
    db = get_database()
    resultado = {
        "custo_medio_ponderado_kg": 0.0,
        "perda_media_percentual": 0.0,
        "custo_real_kg": 0.0,
        "quantidade_estoque_kg": 0.0,
        "qtd_itens": 0,
    }
    if tipo == "CAIXA":
        coll = db["caixas_estoque"]
        match = {"produto_base": produto_base, "status": "EM_ESTOQUE"}
        soma_peso = 0.0
        soma_custo = 0.0
        for doc in coll.find(match):
            peso = float(doc.get("peso_atual_kg") or 0)
            valor_kg = float(doc.get("valor_kg") or 0)
            if peso > 0:
                soma_peso += peso
                soma_custo += valor_kg * peso
                resultado["qtd_itens"] += 1
        if soma_peso > 0:
            resultado["custo_medio_ponderado_kg"] = round(soma_custo / soma_peso, 2)
            resultado["quantidade_estoque_kg"] = round(soma_peso, 3)
        resultado["perda_media_percentual"] = _perda_media_caixa(produto_base)
    else:
        coll = db["produtos_derivados"]
        match = {"produto": produto_base, "peso_disponivel_kg": {"$gt": 0}}
        soma_peso = 0.0
        soma_custo = 0.0
        for doc in coll.find(match):
            peso = float(doc.get("peso_disponivel_kg") or 0)
            custo_kg = float(doc.get("custo_kg") or 0)
            if peso > 0:
                soma_peso += peso
                soma_custo += custo_kg * peso
                resultado["qtd_itens"] += 1
        if soma_peso > 0:
            resultado["custo_medio_ponderado_kg"] = round(soma_custo / soma_peso, 2)
            resultado["quantidade_estoque_kg"] = round(soma_peso, 3)
        resultado["perda_media_percentual"] = _perda_media_processado(produto_base)

    # Custo real considerando perda: custo / (1 - perda/100). Se perda >= 100, usa só custo.
    perda = resultado["perda_media_percentual"]
    custo_medio = resultado["custo_medio_ponderado_kg"]
    if perda >= 100:
        resultado["custo_real_kg"] = round(custo_medio, 2)
    else:
        fator = 1.0 - (perda / 100.0)
        resultado["custo_real_kg"] = round(custo_medio / fator, 2) if fator > 0 else round(custo_medio, 2)
    return resultado


def obter_preco_ativo(produto_base: str, tipo: str) -> Optional[float]:
    """
    Retorna o preço de venda por kg ativo para (produto_base, tipo), ou None.
    Usado nas vendas para preencher preço automaticamente.
    """
    coll = get_precificacao_collection()
    doc = coll.find_one({"produto_base": produto_base, "tipo": tipo, "ativo": True})
    if not doc:
        return None
    preco = doc.get("preco_venda_kg")
    return float(preco) if preco is not None else None


def listar_precificacoes_ativas() -> List[Dict[str, Any]]:
    """Lista registros de precificação ativos para tabela de preços (PDF)."""
    coll = get_precificacao_collection()
    cursor = coll.find({"ativo": True}).sort([("tipo", 1), ("nome_comercial", 1)])
    saida = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        saida.append(doc)
    return saida


def listar_precificacoes_completo() -> List[Dict[str, Any]]:
    """Lista todos os registros ativos para tela de listagem (com dados formatados)."""
    coll = get_precificacao_collection()
    cursor = coll.find({"ativo": True}).sort([("tipo", 1), ("nome_comercial", 1)])
    saida = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc["preco_venda_kg"] = float(doc.get("preco_venda_kg") or 0)
        saida.append(doc)
    return saida


def salvar_precificacao(
    produto_base: str,
    tipo: str,
    nome_comercial: str,
    preco_venda_kg: float,
    margem_percentual: Optional[float] = None,
    custo_real_kg: float = 0,
    custo_medio_ponderado_kg: float = 0,
    perda_media_percentual: float = 0,
    quantidade_estoque_kg: float = 0,
) -> Dict[str, Any]:
    """
    Cria novo registro de precificação. Desativa o anterior com mesmo (produto_base, tipo).
    Não sobrescreve histórico (novo doc com ativo=True, antigo ativo=False).
    """
    coll = get_precificacao_collection()
    coll.update_many(
        {"produto_base": produto_base, "tipo": tipo},
        {"$set": {"ativo": False}},
    )
    now = datetime.utcnow()
    doc = {
        "produto_base": produto_base,
        "tipo": tipo,
        "nome_comercial": (nome_comercial or "").strip() or f"{produto_base} – {tipo}",
        "preco_venda_kg": round(float(preco_venda_kg), 2),
        "margem_percentual": round(float(margem_percentual), 2) if margem_percentual is not None else None,
        "custo_real_kg": round(float(custo_real_kg), 2),
        "custo_medio_ponderado_kg": round(float(custo_medio_ponderado_kg), 2),
        "perda_media_percentual": round(float(perda_media_percentual), 2),
        "quantidade_estoque_kg": round(float(quantidade_estoque_kg), 3),
        "ativo": True,
        "created_at": now,
        "updated_at": now,
    }
    result = coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    return doc


def classificar_margem(custo_real_kg: float, preco_venda_kg: float) -> str:
    """
    Retorna: 'lucrativo' | 'margem_baixa' | 'prejuizo'.
    Lucrativo: margem >= 20%; Margem baixa: 0 <= margem < 20%; Prejuízo: preco < custo.
    """
    if custo_real_kg <= 0:
        return "lucrativo" if preco_venda_kg > 0 else "margem_baixa"
    margem = ((preco_venda_kg - custo_real_kg) / custo_real_kg) * 100
    if preco_venda_kg < custo_real_kg:
        return "prejuizo"
    if margem >= 20:
        return "lucrativo"
    return "margem_baixa"
