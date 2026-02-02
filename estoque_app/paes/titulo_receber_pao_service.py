"""
Service para TituloReceberPao (módulo PÃES — Financeiro).
Títulos a receber são gerados automaticamente a partir dos planos ATIVOS.
Collection: titulos_receber_pao
Documento: plano_id, cliente_id, valor, data_vencimento, status (PENDENTE/PAGO/ATRASADO),
           data_pagamento, forma_pagamento, observacoes, created_at, updated_at
"""
from datetime import datetime, date, timedelta
from calendar import monthrange
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database

from estoque_app.paes.plano_entrega_pao_service import get_planos_collection
from estoque_app.paes.cliente_pao_service import get_clientes_pao_collection

# Python weekday(): 0=Monday=SEG, 1=TER, 2=QUA, 3=QUI, 4=SEX, 5=SAB, 6=DOM
_WEEKDAY_TO_DIA = ("SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM")
_DIA_TO_WEEKDAY = {d: i for i, d in enumerate(_WEEKDAY_TO_DIA)}

FORMAS_PAGAMENTO = ("Dinheiro", "Pix", "Cartão", "Transferência")


def get_titulos_collection():
    """Retorna a collection titulos_receber_pao."""
    return get_database()["titulos_receber_pao"]


def _data_to_dia_semana(d: date) -> str:
    """Retorna SEG, TER, ... para uma data."""
    return _WEEKDAY_TO_DIA[d.weekday()]


def _enriquecer_titulo(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Adiciona id, nome_cliente, tipo_plano, data_vencimento_fmt, dias_atraso (se atrasado)."""
    doc["id"] = str(doc["_id"])
    cliente_id = doc.get("cliente_id")
    plano_id = doc.get("plano_id")
    if cliente_id:
        try:
            c = get_clientes_pao_collection().find_one(
                {"_id": ObjectId(cliente_id) if isinstance(cliente_id, str) else cliente_id}
            )
            doc["nome_cliente"] = c.get("nome", "") if c else ""
        except Exception:
            doc["nome_cliente"] = ""
    else:
        doc["nome_cliente"] = ""
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
    dv = doc.get("data_vencimento")
    doc["data_vencimento_fmt"] = dv.strftime("%d/%m/%Y") if dv and hasattr(dv, "strftime") else (str(dv)[:10] if dv else "")
    doc["data_vencimento_iso"] = dv.strftime("%Y-%m-%d") if dv and hasattr(dv, "strftime") else (str(dv)[:10] if dv else "")
    dp = doc.get("data_pagamento")
    doc["data_pagamento_fmt"] = dp.strftime("%d/%m/%Y") if dp and hasattr(dp, "strftime") else (str(dp)[:10] if dp else "")
    hoje = date.today()
    if doc.get("status") == "PENDENTE" and dv:
        d_venc = dv.date() if hasattr(dv, "date") else dv
        if d_venc < hoje:
            doc["dias_atraso"] = (hoje - d_venc).days
        else:
            doc["dias_atraso"] = 0
    else:
        doc["dias_atraso"] = 0
    return doc


def gerar_titulos_para_periodo(data_inicio: date, data_fim: date) -> int:
    """
    Gera títulos a receber para o período com base nos planos ATIVOS.
    DIARIO: 1 título por dia (dias_entrega), vencimento = data da entrega.
    SEMANAL: 1 título por semana, vencimento = primeiro dia em dias_entrega da semana.
    MENSAL: 1 título por mês, vencimento = mesmo dia do mês que data_pagamento do plano.
    Não duplica títulos existentes (plano_id + data_vencimento).
    Retorna quantidade de títulos criados.
    """
    planos_coll = get_planos_collection()
    titulos_coll = get_titulos_collection()
    criados = 0
    planos = list(planos_coll.find({"status": "ATIVO"}))
    if not planos:
        return 0

    for plano in planos:
        plano_id = plano["_id"]
        cliente_id = plano.get("cliente_id")
        valor = float(plano.get("valor_total_plano") or 0)
        tipo = (plano.get("tipo_plano") or "SEMANAL").strip().upper()
        dias_entrega = plano.get("dias_entrega") or []
        data_pag_plano = plano.get("data_pagamento")
        dia_mes_plano = data_pag_plano.day if data_pag_plano and hasattr(data_pag_plano, "day") else 5

        if tipo == "DIARIO":
            for dia in range((data_fim - data_inicio).days + 1):
                d = data_inicio + timedelta(days=dia)
                if _data_to_dia_semana(d) not in dias_entrega:
                    continue
                d_dt = datetime(d.year, d.month, d.day)
                if titulos_coll.find_one({"plano_id": plano_id, "data_vencimento": d_dt}):
                    continue
                now = datetime.utcnow()
                titulos_coll.insert_one({
                    "plano_id": plano_id,
                    "cliente_id": cliente_id,
                    "valor": round(valor, 2),
                    "data_vencimento": d_dt,
                    "status": "PENDENTE",
                    "data_pagamento": None,
                    "forma_pagamento": None,
                    "observacoes": "",
                    "created_at": now,
                    "updated_at": now,
                })
                criados += 1

        elif tipo == "SEMANAL":
            # Primeiro dia em dias_entrega define o dia de vencimento da semana (ex: TER = terça)
            if not dias_entrega:
                continue
            primeiro_dia = (dias_entrega[0] or "SEG").strip().upper() if dias_entrega else "SEG"
            offset = _DIA_TO_WEEKDAY.get(primeiro_dia, 0)
            # Percorre cada semana no período (segunda-feira como início)
            segunda = data_inicio - timedelta(days=data_inicio.weekday())
            while segunda <= data_fim:
                vencimento = segunda + timedelta(days=offset)
                if data_inicio <= vencimento <= data_fim:
                    v_dt = datetime(vencimento.year, vencimento.month, vencimento.day)
                    if not titulos_coll.find_one({"plano_id": plano_id, "data_vencimento": v_dt}):
                        now = datetime.utcnow()
                        titulos_coll.insert_one({
                            "plano_id": plano_id,
                            "cliente_id": cliente_id,
                            "valor": round(valor, 2),
                            "data_vencimento": v_dt,
                            "status": "PENDENTE",
                            "data_pagamento": None,
                            "forma_pagamento": None,
                            "observacoes": "",
                            "created_at": now,
                            "updated_at": now,
                        })
                        criados += 1
                segunda += timedelta(days=7)

        else:  # MENSAL
            mes_atual = data_inicio.replace(day=1)
            while mes_atual <= data_fim:
                _, ultimo = monthrange(mes_atual.year, mes_atual.month)
                dia_venc = min(dia_mes_plano, ultimo)
                vencimento = date(mes_atual.year, mes_atual.month, dia_venc)
                if data_inicio <= vencimento <= data_fim:
                    v_dt = datetime(vencimento.year, vencimento.month, vencimento.day)
                    if not titulos_coll.find_one({"plano_id": plano_id, "data_vencimento": v_dt}):
                        now = datetime.utcnow()
                        titulos_coll.insert_one({
                            "plano_id": plano_id,
                            "cliente_id": cliente_id,
                            "valor": round(valor, 2),
                            "data_vencimento": v_dt,
                            "status": "PENDENTE",
                            "data_pagamento": None,
                            "forma_pagamento": None,
                            "observacoes": "",
                            "created_at": now,
                            "updated_at": now,
                        })
                        criados += 1
                if mes_atual.month == 12:
                    mes_atual = date(mes_atual.year + 1, 1, 1)
                else:
                    mes_atual = date(mes_atual.year, mes_atual.month + 1, 1)

    return criados


def listar_pendentes_agrupados() -> Dict[str, List[Dict[str, Any]]]:
    """
    Lista títulos PENDENTE agrupados em: esta_semana, semana_que_vem, em_atraso.
    Em atraso = data_vencimento < hoje e status PENDENTE.
    """
    titulos_coll = get_titulos_collection()
    hoje = date.today()
    seg_hoje = hoje - timedelta(days=hoje.weekday())
    fim_esta_semana = seg_hoje + timedelta(days=6)
    seg_proxima = fim_esta_semana + timedelta(days=1)
    fim_proxima = seg_proxima + timedelta(days=6)

    def em_intervalo(d_venc, i_inicio, i_fim):
        if not d_venc:
            return False
        d = d_venc.date() if hasattr(d_venc, "date") else d_venc
        return i_inicio <= d <= i_fim

    esta_semana = []
    semana_que_vem = []
    em_atraso = []

    for doc in titulos_coll.find({"status": "PENDENTE"}).sort("data_vencimento", 1):
        _enriquecer_titulo(doc)
        dv = doc.get("data_vencimento")
        if not dv:
            continue
        d_venc = dv.date() if hasattr(dv, "date") else dv
        if d_venc < hoje:
            em_atraso.append(doc)
        elif em_intervalo(dv, seg_hoje, fim_esta_semana):
            esta_semana.append(doc)
        elif em_intervalo(dv, seg_proxima, fim_proxima):
            semana_que_vem.append(doc)

    return {"esta_semana": esta_semana, "semana_que_vem": semana_que_vem, "em_atraso": em_atraso}


def listar_pagos(periodo_inicio: date, periodo_fim: date) -> List[Dict[str, Any]]:
    """Lista títulos PAGO com data_pagamento no período. Retorna total_recebido também."""
    titulos_coll = get_titulos_collection()
    d_ini = datetime(periodo_inicio.year, periodo_inicio.month, periodo_inicio.day)
    d_fim = datetime(periodo_fim.year, periodo_fim.month, periodo_fim.day, 23, 59, 59, 999999)
    cursor = titulos_coll.find({
        "status": "PAGO",
        "data_pagamento": {"$gte": d_ini, "$lte": d_fim},
    }).sort("data_pagamento", -1)
    saida = []
    total = 0.0
    for doc in cursor:
        _enriquecer_titulo(doc)
        saida.append(doc)
        total += float(doc.get("valor", 0))
    return saida, round(total, 2)


def obter_por_id(titulo_id: str) -> Optional[Dict[str, Any]]:
    """Retorna um título por id ou None. Enriquece."""
    coll = get_titulos_collection()
    try:
        doc = coll.find_one({"_id": ObjectId(titulo_id)})
    except Exception:
        return None
    if not doc:
        return None
    return _enriquecer_titulo(doc)


def registrar_pagamento(
    titulo_id: str,
    data_pagamento,
    forma_pagamento: str = "",
    observacoes: str = "",
) -> bool:
    """Marca título como PAGO, define data_pagamento, forma_pagamento, observacoes. Retorna True se atualizou."""
    coll = get_titulos_collection()
    try:
        oid = ObjectId(titulo_id)
    except Exception:
        return False
    if not data_pagamento:
        return False
    if hasattr(data_pagamento, "date"):
        data_pag_dt = datetime(data_pagamento.year, data_pagamento.month, data_pagamento.day)
    else:
        try:
            data_pag_dt = datetime.strptime(str(data_pagamento)[:10], "%Y-%m-%d")
        except Exception:
            return False
    result = coll.update_one(
        {"_id": oid, "status": "PENDENTE"},
        {"$set": {
            "status": "PAGO",
            "data_pagamento": data_pag_dt,
            "forma_pagamento": (forma_pagamento or "").strip() or None,
            "observacoes": (observacoes or "").strip() or "",
            "updated_at": datetime.utcnow(),
        }},
    )
    return result.modified_count == 1
