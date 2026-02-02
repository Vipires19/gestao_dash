"""
Service para vendas de produtos processados (Fase 3).
Usa collection vendas com schema: data_venda, tipo_venda, itens, resumo_financeiro, divisao_lucro.
Custo real, lucro e divisão cliente/sócio.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database

from estoque_app.services.configuracao_service import obter_divisao_lucro_padrao
from estoque_app.services.produto_derivado_service import (
    get_produtos_derivados_collection,
    obter_por_id as obter_produto_derivado,
    reduzir_peso as reduzir_peso_derivado,
)


def get_vendas_collection():
    """Retorna a collection vendas."""
    return get_database()["vendas"]


def _divisao_lucro_efetiva(
    divisao_venda: Optional[Dict[str, Any]],
    divisao_produto: Optional[Dict[str, Any]],
) -> Dict[str, int]:
    """Hierarquia: venda > produto > configuração padrão."""
    if divisao_venda and "cliente_percentual" in divisao_venda:
        return {
            "cliente_percentual": int(divisao_venda.get("cliente_percentual", 70)),
            "socio_percentual": int(divisao_venda.get("socio_percentual", 30)),
        }
    if divisao_produto and "cliente_percentual" in divisao_produto:
        return {
            "cliente_percentual": int(divisao_produto.get("cliente_percentual", 70)),
            "socio_percentual": int(divisao_produto.get("socio_percentual", 30)),
        }
    return obter_divisao_lucro_padrao()


def obter_venda_processado_por_id(venda_id: str) -> Optional[Dict[str, Any]]:
    """Retorna uma venda de processados pelo id, ou None se não existir."""
    coll = get_vendas_collection()
    try:
        doc = coll.find_one({"_id": ObjectId(venda_id), "tipo_venda": {"$exists": True}})
    except Exception:
        return None
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    dv = doc.get("data_venda")
    doc["data_venda_fmt"] = dv.strftime("%d/%m/%Y") if dv and hasattr(dv, "strftime") else ""
    resumo = doc.get("resumo_financeiro") or {}
    doc["valor_total_venda"] = resumo.get("valor_total_venda", 0)
    return doc


def listar_vendas_processados() -> List[Dict[str, Any]]:
    """
    Lista vendas com schema Fase 3 (tipo_venda presente).
    Ordena por data_venda desc, created_at desc.
    """
    coll = get_vendas_collection()
    cursor = coll.find({"tipo_venda": {"$exists": True}}).sort(
        [("data_venda", -1), ("created_at", -1)]
    )
    saida = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        dv = doc.get("data_venda")
        doc["data_venda_fmt"] = (
            dv.strftime("%d/%m/%Y") if dv and hasattr(dv, "strftime") else ""
        )
        resumo = doc.get("resumo_financeiro") or {}
        doc["valor_total_venda"] = resumo.get("valor_total_venda", 0)
        div = doc.get("divisao_lucro") or {}
        doc["lucro_cliente"] = div.get("lucro_cliente", 0)
        doc["lucro_socio"] = div.get("lucro_socio", 0)
        saida.append(doc)
    return saida


def criar_venda_processado(
    data_venda,
    tipo_venda: str,
    itens: List[Dict[str, Any]],
    divisao_lucro_venda: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Registra uma venda de produtos processados.
    itens: [{ produto_id (produto_derivado id), produto, peso_vendido_kg, preco_venda_kg }]
    Valida peso <= peso_disponivel; calcula custo, lucro; aplica divisão; atualiza estoque derivado.
    """
    if tipo_venda not in ("PROPRIA", "PARCERIA"):
        raise ValueError("tipo_venda deve ser PROPRIA ou PARCERIA.")
    if not itens:
        raise ValueError("A venda deve ter ao menos um item.")

    if hasattr(data_venda, "strftime"):
        data_venda_dt = data_venda
    else:
        try:
            data_venda_dt = datetime.strptime(str(data_venda)[:10], "%Y-%m-%d")
        except Exception:
            raise ValueError("Data da venda inválida.")

    itens_validados = []
    for item in itens:
        produto_id = item.get("produto_id")
        peso_vendido = float(item.get("peso_vendido_kg") or 0)
        preco_venda_kg = float(item.get("preco_venda_kg") or 0)
        produto_nome = (item.get("produto") or "").strip()
        if not produto_id or peso_vendido <= 0:
            continue
        pd = obter_produto_derivado(produto_id)
        if not pd:
            raise ValueError(f"Produto derivado não encontrado: {produto_id}")
        peso_disp = float(pd.get("peso_disponivel_kg") or 0)
        if peso_vendido > peso_disp:
            raise ValueError(
                f"Peso vendido ({peso_vendido} kg) excede o disponível ({peso_disp} kg) para '{pd.get('produto', '')}'."
            )
        custo_kg = float(pd.get("custo_kg") or 0)
        custo_total_item = round(custo_kg * peso_vendido, 2)
        valor_total_venda_item = round(preco_venda_kg * peso_vendido, 2)
        lucro_item = round(valor_total_venda_item - custo_total_item, 2)
        itens_validados.append({
            "produto_id": produto_id,
            "produto": produto_nome or pd.get("produto", ""),
            "peso_vendido_kg": round(peso_vendido, 3),
            "preco_venda_kg": round(preco_venda_kg, 2),
            "valor_total_venda": valor_total_venda_item,
            "custo_total_item": custo_total_item,
            "lucro_item": lucro_item,
            "divisao_produto": pd.get("divisao_lucro"),
        })

    if not itens_validados:
        raise ValueError("Nenhum item válido na venda.")

    valor_total_venda = sum(i["valor_total_venda"] for i in itens_validados)
    custo_total = sum(i["custo_total_item"] for i in itens_validados)
    lucro_total = round(valor_total_venda - custo_total, 2)

    divisao = _divisao_lucro_efetiva(divisao_lucro_venda, itens_validados[0].get("divisao_produto"))
    cliente_pct = divisao["cliente_percentual"] / 100.0
    socio_pct = divisao["socio_percentual"] / 100.0
    lucro_cliente = round(lucro_total * cliente_pct, 2)
    lucro_socio = round(lucro_total * socio_pct, 2)

    now = datetime.utcnow()
    itens_salvar = []
    for i in itens_validados:
        itens_salvar.append({
            "produto_id": i["produto_id"],
            "produto": i["produto"],
            "peso_vendido_kg": i["peso_vendido_kg"],
            "preco_venda_kg": i["preco_venda_kg"],
            "valor_total_venda": i["valor_total_venda"],
            "custo_total_item": i["custo_total_item"],
            "lucro_item": i["lucro_item"],
        })

    venda_doc = {
        "data_venda": data_venda_dt,
        "tipo_venda": tipo_venda,
        "itens": itens_salvar,
        "resumo_financeiro": {
            "valor_total_venda": round(valor_total_venda, 2),
            "custo_total": round(custo_total, 2),
            "lucro_total": lucro_total,
        },
        "divisao_lucro": {
            "cliente_percentual": divisao["cliente_percentual"],
            "socio_percentual": divisao["socio_percentual"],
            "lucro_cliente": lucro_cliente,
            "lucro_socio": lucro_socio,
        },
        "valor_total_venda": round(valor_total_venda, 2),
        "created_at": now,
    }

    coll = get_vendas_collection()
    result = coll.insert_one(venda_doc)
    venda_doc["_id"] = result.inserted_id
    venda_doc["id"] = str(result.inserted_id)

    for i in itens_validados:
        reduzir_peso_derivado(i["produto_id"], i["peso_vendido_kg"])

    return venda_doc
