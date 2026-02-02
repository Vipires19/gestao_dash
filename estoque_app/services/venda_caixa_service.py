"""
Service para vendas de caixas (Emporium Prime).
Collection: vendas_caixas.
Venda de caixas inteiras por código; atualiza status da caixa para VENDIDA.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database

from estoque_app.services.configuracao_service import obter_divisao_lucro_padrao
from estoque_app.services.caixa_estoque_service import get_caixas_collection, obter_caixa_por_id


def get_vendas_caixas_collection():
    """Retorna a collection vendas_caixas."""
    return get_database()["vendas_caixas"]


def _divisao_efetiva(divisao_venda: Optional[Dict[str, Any]]) -> Dict[str, int]:
    """Retorna divisão da venda ou padrão."""
    if divisao_venda and "cliente_percentual" in divisao_venda:
        return {
            "cliente_percentual": int(divisao_venda.get("cliente_percentual", 70)),
            "socio_percentual": int(divisao_venda.get("socio_percentual", 30)),
        }
    return obter_divisao_lucro_padrao()


def criar_venda_caixa(
    data_venda,
    tipo_venda: str,
    itens: List[Dict[str, Any]],
    divisao_lucro_venda: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Registra uma venda de caixas.
    itens: [{ caixa_id, codigo_caixa, produto_base, peso_kg, custo_kg, valor_venda_kg }]
    Valida caixa EM_ESTOQUE; calcula custo e venda por item; atualiza status para VENDIDA.
    """
    if tipo_venda not in ("PROPRIA", "PARCERIA"):
        raise ValueError("tipo_venda deve ser PROPRIA ou PARCERIA.")
    if not itens:
        raise ValueError("A venda deve ter ao menos uma caixa.")

    if hasattr(data_venda, "strftime"):
        data_venda_dt = data_venda
    else:
        try:
            data_venda_dt = datetime.strptime(str(data_venda)[:10], "%Y-%m-%d")
        except Exception:
            raise ValueError("Data da venda inválida.")

    caixas_coll = get_caixas_collection()
    itens_validados = []
    for item in itens:
        caixa_id = item.get("caixa_id")
        peso_kg = float(item.get("peso_kg") or 0)
        custo_kg = float(item.get("custo_kg") or 0)
        valor_venda_kg = float(item.get("valor_venda_kg") or 0)
        codigo = (item.get("codigo_caixa") or "").strip()
        produto_base = (item.get("produto_base") or "").strip()
        if not caixa_id or peso_kg <= 0:
            continue
        try:
            oid = ObjectId(caixa_id)
        except Exception:
            raise ValueError(f"ID de caixa inválido: {caixa_id}")
        caixa = caixas_coll.find_one({"_id": oid})
        if not caixa:
            raise ValueError(f"Caixa não encontrada: {caixa_id}")
        if caixa.get("status") != "EM_ESTOQUE":
            raise ValueError(f"Caixa {codigo or caixa_id} não está disponível (status: {caixa.get('status')}).")
        peso_atual = float(caixa.get("peso_atual_kg") or 0)
        if abs(peso_kg - peso_atual) > 0.001:
            peso_kg = peso_atual
        custo_total_item = round(custo_kg * peso_kg, 2)
        valor_venda_item = round(valor_venda_kg * peso_kg, 2)
        lucro_item = round(valor_venda_item - custo_total_item, 2)
        itens_validados.append({
            "caixa_id": caixa_id,
            "codigo_caixa": codigo or caixa.get("codigo_caixa", ""),
            "produto_base": produto_base or caixa.get("produto_base", ""),
            "peso_kg": round(peso_kg, 3),
            "custo_kg": round(custo_kg, 2),
            "valor_venda_kg": round(valor_venda_kg, 2),
            "custo_total_item": custo_total_item,
            "valor_venda_item": valor_venda_item,
            "lucro_item": lucro_item,
        })

    if not itens_validados:
        raise ValueError("Nenhum item válido na venda.")

    valor_total_venda = sum(i["valor_venda_item"] for i in itens_validados)
    custo_total = sum(i["custo_total_item"] for i in itens_validados)
    lucro_total = round(valor_total_venda - custo_total, 2)

    divisao = _divisao_efetiva(divisao_lucro_venda)
    cliente_pct = divisao["cliente_percentual"] / 100.0
    socio_pct = divisao["socio_percentual"] / 100.0
    lucro_cliente = round(lucro_total * cliente_pct, 2)
    lucro_socio = round(lucro_total * socio_pct, 2)

    now = datetime.utcnow()
    itens_salvar = []
    for i in itens_validados:
        itens_salvar.append({
            "caixa_id": i["caixa_id"],
            "codigo_caixa": i["codigo_caixa"],
            "produto_base": i["produto_base"],
            "peso_kg": i["peso_kg"],
            "custo_kg": i["custo_kg"],
            "valor_venda_kg": i["valor_venda_kg"],
            "custo_total_item": i["custo_total_item"],
            "valor_venda_item": i["valor_venda_item"],
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
        "created_at": now,
    }

    coll = get_vendas_caixas_collection()
    result = coll.insert_one(venda_doc)
    venda_doc["_id"] = result.inserted_id
    venda_doc["id"] = str(result.inserted_id)

    for i in itens_validados:
        try:
            caixas_coll.update_one(
                {"_id": ObjectId(i["caixa_id"])},
                {"$set": {"status": "VENDIDA"}},
            )
        except Exception:
            pass

    return venda_doc


def obter_venda_caixa_por_id(venda_id: str) -> Optional[Dict[str, Any]]:
    """Retorna uma venda de caixas pelo id, ou None se não existir."""
    coll = get_vendas_caixas_collection()
    try:
        doc = coll.find_one({"_id": ObjectId(venda_id)})
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


def listar_vendas_caixas() -> List[Dict[str, Any]]:
    """Lista vendas de caixas ordenadas por data_venda desc."""
    coll = get_vendas_caixas_collection()
    cursor = coll.find().sort([("data_venda", -1), ("created_at", -1)])
    saida = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        dv = doc.get("data_venda")
        doc["data_venda_fmt"] = dv.strftime("%d/%m/%Y") if dv and hasattr(dv, "strftime") else ""
        resumo = doc.get("resumo_financeiro") or {}
        doc["valor_total_venda"] = resumo.get("valor_total_venda", 0)
        div = doc.get("divisao_lucro") or {}
        doc["lucro_cliente"] = div.get("lucro_cliente", 0)
        doc["lucro_socio"] = div.get("lucro_socio", 0)
        saida.append(doc)
    return saida
