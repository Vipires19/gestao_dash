"""
Service para EntregaPao (módulo PÃES).
Entregas são geradas automaticamente a partir dos planos ATIVOS.
Collection: entregas_pao
Documento: plano_id, cliente_id, data_entrega, dia_semana, horario_entrega,
           quantidade_paes, status (PENDENTE/ENTREGUE), data_confirmacao, created_at, updated_at
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database

from estoque_app.paes.plano_entrega_pao_service import get_planos_collection
from estoque_app.paes.cliente_pao_service import get_clientes_pao_collection

# Python weekday(): 0=Monday=SEG, 1=TER, 2=QUA, 3=QUI, 4=SEX, 5=SAB, 6=DOM
_WEEKDAY_TO_DIA = ("SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM")


def get_entregas_collection():
    """Retorna a collection entregas_pao."""
    return get_database()["entregas_pao"]


def _data_to_dia_semana(d: date) -> str:
    """Retorna SEG, TER, ... para uma data."""
    return _WEEKDAY_TO_DIA[d.weekday()]


def gerar_entregas_para_periodo(data_inicio: date, data_fim: date) -> int:
    """
    Gera entregas para o período com base nos planos ATIVOS.
    Para cada plano ATIVO e cada data no intervalo: se dia_semana está em dias_entrega,
    cria entrega se ainda não existir (plano_id + data_entrega único).
    Retorna quantidade de entregas criadas.
    """
    planos_coll = get_planos_collection()
    entregas_coll = get_entregas_collection()
    criadas = 0
    planos = list(planos_coll.find({"status": "ATIVO"}))
    if not planos:
        return 0
    delta = data_fim - data_inicio
    for dia in range(delta.days + 1):
        d = data_inicio + timedelta(days=dia)
        dia_semana = _data_to_dia_semana(d)
        d_dt = datetime(d.year, d.month, d.day)
        for plano in planos:
            dias_entrega = plano.get("dias_entrega") or []
            if dia_semana not in dias_entrega:
                continue
            plano_id = plano["_id"]
            existe = entregas_coll.find_one({
                "plano_id": plano_id,
                "data_entrega": d_dt,
            })
            if existe:
                continue
            now = datetime.utcnow()
            doc = {
                "plano_id": plano_id,
                "cliente_id": plano.get("cliente_id"),
                "data_entrega": d_dt,
                "dia_semana": dia_semana,
                "horario_entrega": (plano.get("horario_entrega") or "06:00")[:5],
                "quantidade_paes": int(plano.get("quantidade_paes_por_dia") or 0),
                "status": "PENDENTE",
                "data_confirmacao": None,
                "created_at": now,
                "updated_at": now,
            }
            entregas_coll.insert_one(doc)
            criadas += 1
    return criadas


def _enriquecer_entrega(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Adiciona id, nome_cliente, endereco_cliente, data_entrega_fmt, tipo_plano."""
    doc["id"] = str(doc["_id"])
    cliente_id = doc.get("cliente_id")
    if cliente_id:
        coll_cli = get_clientes_pao_collection()
        try:
            c = coll_cli.find_one({"_id": ObjectId(cliente_id) if isinstance(cliente_id, str) else cliente_id})
            doc["nome_cliente"] = c.get("nome", "") if c else ""
            doc["endereco_cliente"] = c.get("endereco", "") if c else ""
        except Exception:
            doc["nome_cliente"] = ""
            doc["endereco_cliente"] = ""
    else:
        doc["nome_cliente"] = ""
        doc["endereco_cliente"] = ""
    plano_id = doc.get("plano_id")
    if plano_id:
        try:
            p = get_planos_collection().find_one(
                {"_id": ObjectId(plano_id) if isinstance(plano_id, str) else plano_id}
            )
            doc["tipo_plano"] = p.get("tipo_plano", "") if p else ""
        except Exception:
            doc["tipo_plano"] = ""
    else:
        doc["tipo_plano"] = ""
    de = doc.get("data_entrega")
    doc["data_entrega_fmt"] = de.strftime("%d/%m/%Y") if de and hasattr(de, "strftime") else (str(de)[:10] if de else "")
    return doc


def listar_entregas_por_data(data: date) -> List[Dict[str, Any]]:
    """Lista entregas de uma data, ordenadas por horário e nome do cliente. Enriquece com nome e endereço."""
    coll = get_entregas_collection()
    d_inicio = datetime(data.year, data.month, data.day)
    d_fim = d_inicio.replace(hour=23, minute=59, second=59, microsecond=999999)
    cursor = coll.find({"data_entrega": {"$gte": d_inicio, "$lte": d_fim}}).sort([("horario_entrega", 1), ("nome_cliente", 1)])
    saida = []
    for doc in cursor:
        _enriquecer_entrega(doc)
        saida.append(doc)
    # Ordenar por horário (string) e nome
    saida.sort(key=lambda x: (x.get("horario_entrega") or "", x.get("nome_cliente") or ""))
    return saida


def listar_entregas_agrupadas_por_data(data_inicio: date, data_fim: date) -> Dict[str, List[Dict[str, Any]]]:
    """Retorna { "YYYY-MM-DD": [entregas], ... } para o período (apenas datas que têm entregas)."""
    coll = get_entregas_collection()
    d_ini = datetime(data_inicio.year, data_inicio.month, data_inicio.day)
    d_fim = datetime(data_fim.year, data_fim.month, data_fim.day, 23, 59, 59, 999999)
    cursor = coll.find({"data_entrega": {"$gte": d_ini, "$lte": d_fim}}).sort("data_entrega", 1)
    agrupado = {}
    for doc in cursor:
        _enriquecer_entrega(doc)
        de = doc.get("data_entrega")
        key = de.strftime("%Y-%m-%d") if de and hasattr(de, "strftime") else str(de)[:10]
        if key not in agrupado:
            agrupado[key] = []
        agrupado[key].append(doc)
    for key in agrupado:
        agrupado[key].sort(key=lambda x: (x.get("horario_entrega") or "", x.get("nome_cliente") or ""))
    return agrupado


def obter_por_id(entrega_id: str) -> Optional[Dict[str, Any]]:
    """Retorna uma entrega por id ou None. Enriquece."""
    coll = get_entregas_collection()
    try:
        doc = coll.find_one({"_id": ObjectId(entrega_id)})
    except Exception:
        return None
    if not doc:
        return None
    return _enriquecer_entrega(doc)


def confirmar_entrega(entrega_id: str) -> bool:
    """Marca entrega como ENTREGUE e define data_confirmacao = now. Retorna True se encontrou e atualizou."""
    coll = get_entregas_collection()
    try:
        oid = ObjectId(entrega_id)
    except Exception:
        return False
    result = coll.update_one(
        {"_id": oid, "status": "PENDENTE"},
        {"$set": {"status": "ENTREGUE", "data_confirmacao": datetime.utcnow(), "updated_at": datetime.utcnow()}},
    )
    return result.modified_count == 1


def resumo_producao_por_data(data: date) -> Dict[str, Any]:
    """
    Retorna resumo de produção para uma data: cada entrega = 1 saco, tamanho do saco = quantidade_paes.
    Agrupamento dinâmico: {quantidade_paes: total_de_sacos}. Retorna itens (ordenados) e total_paes.
    """
    entregas = listar_entregas_por_data(data)
    producao = {}
    total_paes = 0
    for entrega in entregas:
        qtd = entrega.get("quantidade_paes") or 0
        if qtd <= 0:
            continue
        producao[qtd] = producao.get(qtd, 0) + 1
        total_paes += qtd
    # itens: lista (quantidade_paes, num_sacos) ordenada do menor para o maior
    itens = sorted(producao.items(), key=lambda x: x[0])
    return {
        "producao": producao,
        "itens": itens,
        "total_paes": total_paes,
        "total_entregas": len(entregas),
    }
