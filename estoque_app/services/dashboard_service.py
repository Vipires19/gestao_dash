"""
Service para dados do dashboard.

Localização: estoque_app/services/dashboard_service.py

Funções para agregação de dados do dia (vendas, faturamento, estoque baixo).
Acesso direto ao MongoDB via pymongo (sem ORM).
"""
from datetime import datetime, timedelta
from core.database import get_database


def _hoje_range():
    """
    Retorna (início, fim) do dia atual em UTC para filtrar created_at.
    Início: 00:00:00, Fim: 23:59:59.999
    """
    now = datetime.utcnow()
    inicio = datetime(now.year, now.month, now.day, 0, 0, 0, 0)
    fim = datetime(now.year, now.month, now.day, 23, 59, 59, 999000)
    return inicio, fim


def faturamento_hoje():
    """
    Soma do campo valor_total_venda das vendas realizadas hoje.
    Usa created_at para filtrar pelo dia atual (UTC).
    """
    db = get_database()
    vendas = db["vendas"]
    inicio, fim = _hoje_range()
    pipeline = [
        {"$match": {"created_at": {"$gte": inicio, "$lte": fim}}},
        {"$group": {"_id": None, "total": {"$sum": "$valor_total_venda"}}},
    ]
    result = list(vendas.aggregate(pipeline))
    if not result:
        return 0.0
    return float(result[0]["total"])


def total_vendas_hoje():
    """
    Número total de vendas realizadas hoje (created_at no dia atual UTC).
    """
    db = get_database()
    vendas = db["vendas"]
    inicio, fim = _hoje_range()
    return vendas.count_documents({"created_at": {"$gte": inicio, "$lte": fim}})


def total_produtos_vendidos_hoje():
    """
    Soma da quantidade total de produtos vendidos hoje
    (soma da quantidade de todos os itens das vendas do dia).
    """
    db = get_database()
    vendas = db["vendas"]
    inicio, fim = _hoje_range()
    pipeline = [
        {"$match": {"created_at": {"$gte": inicio, "$lte": fim}}},
        {"$unwind": "$itens"},
        {"$group": {"_id": None, "total": {"$sum": "$itens.quantidade"}}},
    ]
    result = list(vendas.aggregate(pipeline))
    if not result:
        return 0
    return result[0]["total"]


def total_produtos_estoque_baixo():
    """
    Quantidade de produtos com estoque baixo (quantidade <= 5).
    Não altera o banco; apenas conta documentos.
    """
    db = get_database()
    produtos = db["produtos"]
    return produtos.count_documents({"quantidade": {"$lte": 5}})


def despesas_hoje():
    """
    Soma das despesas com data igual a hoje (campo data no dia atual UTC).
    """
    db = get_database()
    despesas = db["despesas"]
    inicio, fim = _hoje_range()
    pipeline = [
        {"$match": {"data": {"$gte": inicio, "$lte": fim}}},
        {"$group": {"_id": None, "total": {"$sum": "$valor"}}},
    ]
    result = list(despesas.aggregate(pipeline))
    if not result:
        return 0.0
    return float(result[0]["total"])


def lucro_hoje():
    """
    Lucro do dia = Faturamento do dia - Despesas do dia.
    """
    return faturamento_hoje() - despesas_hoje()


def despesas_ultimos_7_dias():
    """
    Despesas agrupadas por dia (campo data) nos últimos 7 dias (incluindo hoje).
    Retorna lista pronta para o frontend: [{"data": "dd/mm", "valor": float}, ...].
    Dias sem despesas aparecem com valor 0.
    """
    db = get_database()
    despesas = db["despesas"]
    inicio, fim = _ultimos_7_dias_range()
    pipeline = [
        {"$match": {"data": {"$gte": inicio, "$lte": fim}}},
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$data"},
                    "month": {"$month": "$data"},
                    "day": {"$dayOfMonth": "$data"},
                },
                "total": {"$sum": "$valor"},
            },
        },
    ]
    result = list(despesas.aggregate(pipeline))
    por_dia = {}
    for r in result:
        key = (r["_id"]["year"], r["_id"]["month"], r["_id"]["day"])
        por_dia[key] = float(r["total"])
    now = datetime.utcnow()
    saida = []
    for i in range(6, -1, -1):
        d = now - timedelta(days=i)
        key = (d.year, d.month, d.day)
        valor = por_dia.get(key, 0.0)
        saida.append({"data": d.strftime("%d/%m"), "valor": round(valor, 2)})
    return saida


def maior_despesa_hoje():
    """
    Maior despesa do dia (maior valor entre despesas com data = hoje).
    Retorna {"descricao": str, "valor": float} ou None se não houver despesas hoje.
    """
    db = get_database()
    despesas = db["despesas"]
    inicio, fim = _hoje_range()
    doc = despesas.find_one(
        {"data": {"$gte": inicio, "$lte": fim}},
        sort=[("valor", -1)],
        projection={"descricao": 1, "valor": 1},
    )
    if not doc:
        return None
    return {"descricao": doc.get("descricao", ""), "valor": float(doc.get("valor", 0))}


def _ultimos_7_dias_range():
    """
    Retorna (início do primeiro dia, fim do último dia) dos últimos 7 dias
    (incluindo hoje), em UTC.
    """
    now = datetime.utcnow()
    fim = datetime(now.year, now.month, now.day, 23, 59, 59, 999000)
    inicio_primeiro_dia = now - timedelta(days=6)
    inicio = datetime(
        inicio_primeiro_dia.year,
        inicio_primeiro_dia.month,
        inicio_primeiro_dia.day,
        0, 0, 0, 0,
    )
    return inicio, fim


def faturamento_ultimos_7_dias():
    """
    Faturamento agrupado por dia nos últimos 7 dias (incluindo hoje).
    Retorna lista pronta para o frontend: [{"data": "dd/mm", "valor": float}, ...].
    Dias sem vendas aparecem com valor 0.
    """
    db = get_database()
    vendas = db["vendas"]
    inicio, fim = _ultimos_7_dias_range()

    pipeline = [
        {"$match": {"created_at": {"$gte": inicio, "$lte": fim}}},
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"},
                    "day": {"$dayOfMonth": "$created_at"},
                },
                "total": {"$sum": "$valor_total_venda"},
            },
        },
    ]
    result = list(vendas.aggregate(pipeline))

    # Mapa (year, month, day) -> total
    por_dia = {}
    for r in result:
        key = (r["_id"]["year"], r["_id"]["month"], r["_id"]["day"])
        por_dia[key] = float(r["total"])

    # Lista dos 7 dias (do mais antigo ao mais recente)
    now = datetime.utcnow()
    saida = []
    for i in range(6, -1, -1):
        d = now - timedelta(days=i)
        key = (d.year, d.month, d.day)
        valor = por_dia.get(key, 0.0)
        data_str = d.strftime("%d/%m")
        saida.append({"data": data_str, "valor": round(valor, 2)})
    return saida


def top_5_produtos_ultimos_7_dias():
    """
    Top 5 produtos mais vendidos nos últimos 7 dias (por quantidade).
    Retorna lista pronta para o frontend: [{"nome": str, "quantidade": int}, ...].
    """
    db = get_database()
    vendas = db["vendas"]
    inicio, fim = _ultimos_7_dias_range()

    pipeline = [
        {"$match": {"created_at": {"$gte": inicio, "$lte": fim}}},
        {"$unwind": "$itens"},
        {"$group": {"_id": "$itens.nome", "quantidade": {"$sum": "$itens.quantidade"}}},
        {"$sort": {"quantidade": -1}},
        {"$limit": 5},
        {"$project": {"nome": "$_id", "quantidade": 1, "_id": 0}},
    ]
    result = list(vendas.aggregate(pipeline))
    return [{"nome": r.get("nome", ""), "quantidade": r["quantidade"]} for r in result]


def ultimas_vendas(limit=5):
    """
    Retorna as últimas vendas (mais recentes primeiro), prontas para exibição.
    Cada item tem: id, data (DD/MM HH:MM), quantidade_itens, valor_total_venda.
    """
    db = get_database()
    vendas = db["vendas"]
    cursor = vendas.find().sort("created_at", -1).limit(limit)
    saida = []
    for venda in cursor:
        venda["id"] = str(venda["_id"])
        created = venda.get("created_at")
        venda["data_formatada"] = created.strftime("%d/%m %H:%M") if created else ""
        itens = venda.get("itens", [])
        venda["quantidade_itens"] = sum(item.get("quantidade", 0) for item in itens)
        saida.append(venda)
    return saida


def produto_mais_vendido_hoje():
    """
    Produto com maior quantidade vendida hoje.
    Retorna {"nome": str, "quantidade": int} ou None se não houver vendas hoje.
    """
    db = get_database()
    vendas = db["vendas"]
    inicio, fim = _hoje_range()
    pipeline = [
        {"$match": {"created_at": {"$gte": inicio, "$lte": fim}}},
        {"$unwind": "$itens"},
        {"$group": {"_id": "$itens.nome", "quantidade": {"$sum": "$itens.quantidade"}}},
        {"$sort": {"quantidade": -1}},
        {"$limit": 1},
        {"$project": {"nome": "$_id", "quantidade": 1, "_id": 0}},
    ]
    result = list(vendas.aggregate(pipeline))
    if not result:
        return None
    r = result[0]
    return {"nome": r.get("nome", ""), "quantidade": r["quantidade"]}


def maior_venda_hoje():
    """
    Maior venda do dia (maior valor_total_venda).
    Retorna {"valor": float, "hora": "HH:MM"} ou None se não houver vendas hoje.
    """
    db = get_database()
    vendas = db["vendas"]
    inicio, fim = _hoje_range()
    venda = vendas.find_one(
        {"created_at": {"$gte": inicio, "$lte": fim}},
        sort=[("valor_total_venda", -1)],
        projection={"valor_total_venda": 1, "created_at": 1},
    )
    if not venda:
        return None
    created = venda.get("created_at")
    hora = created.strftime("%H:%M") if created else ""
    return {"valor": float(venda.get("valor_total_venda", 0)), "hora": hora}


def produtos_estoque_critico(limit=10):
    """
    Produtos com estoque crítico (quantidade <= 5).
    Ordenados por quantidade crescente. Retorna lista pronta para exibição
    com id, codigo, nome, quantidade. Limite padrão 10.
    """
    db = get_database()
    produtos = db["produtos"]
    cursor = produtos.find({"quantidade": {"$lte": 5}}).sort("quantidade", 1).limit(limit)
    saida = []
    for p in cursor:
        p["id"] = str(p["_id"])
        saida.append({
            "id": p["id"],
            "codigo": p.get("codigo", ""),
            "nome": p.get("nome", ""),
            "quantidade": p.get("quantidade", 0),
        })
    return saida


def alertas_estoque():
    """
    Lista de mensagens de alerta sobre estoque crítico.
    Ex.: "3 produtos estão com estoque crítico", "MONSTER está com apenas 1 unidade em estoque"
    """
    criticos = produtos_estoque_critico(limit=50)
    alertas = []
    if not criticos:
        return alertas
    n = len(criticos)
    if n == 1:
        alertas.append("1 produto está com estoque crítico")
    else:
        alertas.append(f"{n} produtos estão com estoque crítico")
    for p in criticos:
        if p["quantidade"] == 1:
            alertas.append(f"{p['nome']} está com apenas 1 unidade em estoque")
    return alertas


def alertas_financeiros(faturamento_hoje_val, despesas_hoje_val, lucro_hoje_val):
    """
    Lista de mensagens de alerta financeiro (informativas, sem bloqueio).
    - Despesas de hoje ultrapassaram 50% do faturamento
    - Dia operando no prejuízo
    """
    alertas = []
    if faturamento_hoje_val > 0 and despesas_hoje_val > 0.5 * faturamento_hoje_val:
        alertas.append("Despesas de hoje ultrapassaram 50% do faturamento")
    if lucro_hoje_val <= 0 and (faturamento_hoje_val > 0 or despesas_hoje_val > 0):
        alertas.append("Dia operando no prejuízo")
    return alertas


# --- Análise por período ---

def _periodo_range(periodo):
    """
    Retorna (início, fim) em UTC para o período.
    mes → mês atual; trimestre → últimos 90 dias; geral → (None, None).
    """
    now = datetime.utcnow()
    if periodo == "mes":
        inicio = datetime(now.year, now.month, 1, 0, 0, 0, 0)
        # Último dia do mês
        if now.month == 12:
            fim = datetime(now.year, 12, 31, 23, 59, 59, 999000)
        else:
            fim = datetime(now.year, now.month + 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
        return inicio, fim
    if periodo == "trimestre":
        inicio = now - timedelta(days=90)
        inicio = datetime(inicio.year, inicio.month, inicio.day, 0, 0, 0, 0)
        fim = datetime(now.year, now.month, now.day, 23, 59, 59, 999000)
        return inicio, fim
    return None, None  # geral


def resumo_periodo(periodo):
    """
    Retorna resumo do período: faturamento, despesas, lucro, total_vendas.
    """
    db = get_database()
    vendas = db["vendas"]
    despesas = db["despesas"]
    inicio, fim = _periodo_range(periodo)

    if inicio is None:  # geral
        fat_result = list(vendas.aggregate([{"$group": {"_id": None, "total": {"$sum": "$valor_total_venda"}}}]))
        desp_result = list(despesas.aggregate([{"$group": {"_id": None, "total": {"$sum": "$valor"}}}]))
        total_vendas = vendas.count_documents({})
    else:
        fat_result = list(vendas.aggregate([
            {"$match": {"created_at": {"$gte": inicio, "$lte": fim}}},
            {"$group": {"_id": None, "total": {"$sum": "$valor_total_venda"}}},
        ]))
        desp_result = list(despesas.aggregate([
            {"$match": {"data": {"$gte": inicio, "$lte": fim}}},
            {"$group": {"_id": None, "total": {"$sum": "$valor"}}},
        ]))
        total_vendas = vendas.count_documents({"created_at": {"$gte": inicio, "$lte": fim}})

    fat = float(fat_result[0]["total"]) if fat_result else 0.0
    desp = float(desp_result[0]["total"]) if desp_result else 0.0
    return {
        "faturamento": fat,
        "despesas": desp,
        "lucro": fat - desp,
        "total_vendas": total_vendas,
    }


def _grafico_vendas_por_periodo(periodo):
    """Agrupa vendas por dia ou mês conforme período. Retorna [{"data": str, "valor": float}, ...]."""
    db = get_database()
    vendas = db["vendas"]
    inicio, fim = _periodo_range(periodo)

    if inicio is None:  # geral: agrupar por mês
        pipeline = [
            {"$group": {"_id": {"year": {"$year": "$created_at"}, "month": {"$month": "$created_at"}}, "total": {"$sum": "$valor_total_venda"}}},
            {"$sort": {"_id.year": 1, "_id.month": 1}},
        ]
        result = list(vendas.aggregate(pipeline))
        return [{"data": f"{r['_id']['month']:02d}/{r['_id']['year']}", "valor": round(float(r["total"]), 2)} for r in result]
    if periodo == "mes":
        from calendar import monthrange
        _, ultimo = monthrange(inicio.year, inicio.month)
        por_dia = {}
        pipeline = [
            {"$match": {"created_at": {"$gte": inicio, "$lte": fim}}},
            {"$group": {"_id": {"$dayOfMonth": "$created_at"}, "total": {"$sum": "$valor_total_venda"}}},
        ]
        for r in vendas.aggregate(pipeline):
            por_dia[r["_id"]] = float(r["total"])
        saida = []
        for d in range(1, ultimo + 1):
            saida.append({"data": f"{d:02d}/{inicio.month:02d}", "valor": round(por_dia.get(d, 0.0), 2)})
        return saida
    # trimestre: um ponto por dia (últimos 90 dias)
    pipeline = [
        {"$match": {"created_at": {"$gte": inicio, "$lte": fim}}},
        {"$group": {"_id": {"year": {"$year": "$created_at"}, "month": {"$month": "$created_at"}, "day": {"$dayOfMonth": "$created_at"}}, "total": {"$sum": "$valor_total_venda"}}},
    ]
    result = list(vendas.aggregate(pipeline))
    por_dia = {}
    for r in result:
        key = (r["_id"]["year"], r["_id"]["month"], r["_id"]["day"])
        por_dia[key] = float(r["total"])
    saida = []
    for i in range(90):
        d = datetime.utcnow() - timedelta(days=89 - i)
        key = (d.year, d.month, d.day)
        saida.append({"data": d.strftime("%d/%m"), "valor": round(por_dia.get(key, 0.0), 2)})
    return saida


def _grafico_despesas_por_periodo(periodo):
    """Agrupa despesas por dia ou mês conforme período. Retorna [{"data": str, "valor": float}, ...]."""
    db = get_database()
    despesas = db["despesas"]
    inicio, fim = _periodo_range(periodo)

    if inicio is None:
        pipeline = [
            {"$group": {"_id": {"year": {"$year": "$data"}, "month": {"$month": "$data"}}, "total": {"$sum": "$valor"}}},
            {"$sort": {"_id.year": 1, "_id.month": 1}},
        ]
        result = list(despesas.aggregate(pipeline))
        return [{"data": f"{r['_id']['month']:02d}/{r['_id']['year']}", "valor": round(float(r["total"]), 2)} for r in result]
    if periodo == "mes":
        from calendar import monthrange
        _, ultimo = monthrange(inicio.year, inicio.month)
        pipeline = [
            {"$match": {"data": {"$gte": inicio, "$lte": fim}}},
            {"$group": {"_id": {"$dayOfMonth": "$data"}, "total": {"$sum": "$valor"}}},
        ]
        result = list(despesas.aggregate(pipeline))
        por_dia = {r["_id"]: float(r["total"]) for r in result}
        saida = []
        for d in range(1, ultimo + 1):
            saida.append({"data": f"{d:02d}/{inicio.month:02d}", "valor": round(por_dia.get(d, 0.0), 2)})
        return saida
    pipeline = [
        {"$match": {"data": {"$gte": inicio, "$lte": fim}}},
        {"$group": {"_id": {"year": {"$year": "$data"}, "month": {"$month": "$data"}, "day": {"$dayOfMonth": "$data"}}, "total": {"$sum": "$valor"}}},
    ]
    result = list(despesas.aggregate(pipeline))
    por_dia = {}
    for r in result:
        key = (r["_id"]["year"], r["_id"]["month"], r["_id"]["day"])
        por_dia[key] = float(r["total"])
    saida = []
    for i in range(90):
        d = datetime.utcnow() - timedelta(days=89 - i)
        key = (d.year, d.month, d.day)
        saida.append({"data": d.strftime("%d/%m"), "valor": round(por_dia.get(key, 0.0), 2)})
    return saida


def grafico_faturamento_periodo(periodo):
    """Retorna dados para gráfico de faturamento no período."""
    return _grafico_vendas_por_periodo(periodo)


def grafico_despesas_periodo(periodo):
    """Retorna dados para gráfico de despesas no período."""
    return _grafico_despesas_por_periodo(periodo)


def insights_periodo(periodo):
    """
    Retorna insights do período: produto_mais_vendido, maior_venda, maior_despesa.
    Cada um pode ser None se não houver dados.
    """
    db = get_database()
    vendas = db["vendas"]
    despesas = db["despesas"]
    inicio, fim = _periodo_range(periodo)

    match_vendas = {"$match": {"created_at": {"$gte": inicio, "$lte": fim}}} if inicio is not None else None
    match_despesas = {"$match": {"data": {"$gte": inicio, "$lte": fim}}} if inicio is not None else None

    # Produto mais vendido
    pipe_prod = [{"$unwind": "$itens"}, {"$group": {"_id": "$itens.nome", "quantidade": {"$sum": "$itens.quantidade"}}}, {"$sort": {"quantidade": -1}}, {"$limit": 1}]
    if match_vendas:
        pipe_prod.insert(0, match_vendas)
    result = list(vendas.aggregate(pipe_prod))
    produto_mais_vendido = {"nome": result[0]["_id"], "quantidade": result[0]["quantidade"]} if result else None

    # Maior venda
    pipe_venda = [{"$sort": {"valor_total_venda": -1}}, {"$limit": 1}, {"$project": {"valor_total_venda": 1, "created_at": 1}}]
    if match_vendas is not None:
        pipe_venda.insert(0, match_vendas)
    result = list(vendas.aggregate(pipe_venda))
    if result:
        r = result[0]
        created = r.get("created_at")
        data_fmt = created.strftime("%d/%m/%Y %H:%M") if created and hasattr(created, "strftime") else ""
        maior_venda = {"valor": float(r.get("valor_total_venda", 0)), "data_formatada": data_fmt}
    else:
        maior_venda = None

    # Maior despesa
    pipe_desp = [{"$sort": {"valor": -1}}, {"$limit": 1}, {"$project": {"descricao": 1, "valor": 1}}]
    if match_despesas is not None:
        pipe_desp.insert(0, match_despesas)
    result = list(despesas.aggregate(pipe_desp))
    maior_despesa = {"descricao": result[0]["descricao"], "valor": float(result[0]["valor"])} if result else None

    return {
        "produto_mais_vendido": produto_mais_vendido,
        "maior_venda": maior_venda,
        "maior_despesa": maior_despesa,
    }
