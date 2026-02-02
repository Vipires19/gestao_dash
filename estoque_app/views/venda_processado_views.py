"""
Views para vendas de produtos processados (Fase 3).
Nova venda com custo real, lucro e divisão cliente/sócio.
"""
import json
import logging
from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages

from estoque_app.services.configuracao_service import obter_divisao_lucro_padrao
from estoque_app.services.produto_derivado_service import listar_disponiveis
from estoque_app.services.venda_processado_service import (
    listar_vendas_processados,
    criar_venda_processado,
)
from estoque_app.services.precificacao_service import obter_preco_ativo

logger = logging.getLogger(__name__)


def venda_processado_list(request):
    """Listagem de vendas de produtos processados. Data, tipo, valor total, lucro cliente, lucro sócio."""
    try:
        vendas = listar_vendas_processados()
    except Exception as e:
        messages.error(request, f"Erro ao listar vendas: {e}")
        vendas = []
    return render(request, "estoque_app/vendas_processados/list.html", {"vendas": vendas})


def venda_processado_nova(request):
    """Nova venda de produtos processados. GET: form com produtos derivados; POST: registra venda."""
    hoje = date.today().isoformat()
    divisao_padrao = obter_divisao_lucro_padrao()

    if request.method == "POST":
        return _venda_processado_create_post(request, hoje, divisao_padrao)

    produtos = listar_disponiveis()
    produtos_ctx = []
    for p in produtos:
        try:
            peso = float(p.get("peso_disponivel_kg") or 0)
            custo = float(p.get("custo_kg") or 0)
        except (TypeError, ValueError):
            peso = 0.0
            custo = 0.0
        produto_nome = str(p.get("produto", ""))
        preco_sugerido = obter_preco_ativo(produto_nome, "PROCESSADO")
        produtos_ctx.append({
            "id": str(p.get("id", "")),
            "produto": produto_nome,
            "peso_disponivel_kg": peso,
            "custo_kg": custo,
            "preco_venda_kg": float(preco_sugerido) if preco_sugerido is not None else custo,
        })
    logger.info("venda_processado_nova GET: %d produtos processados disponíveis", len(produtos_ctx))
    return render(request, "estoque_app/vendas_processados/nova.html", {
        "produtos": produtos_ctx,
        "hoje": hoje,
        "divisao_padrao": divisao_padrao,
    })


def _venda_processado_create_post(request, hoje, divisao_padrao):
    data_venda = request.POST.get("data_venda", "").strip()
    tipo_venda = request.POST.get("tipo_venda", "PROPRIA").strip()
    if tipo_venda not in ("PROPRIA", "PARCERIA"):
        tipo_venda = "PROPRIA"

    cliente_pct = request.POST.get("divisao_cliente_percentual", "").strip()
    socio_pct = request.POST.get("divisao_socio_percentual", "").strip()
    divisao_lucro_venda = None
    if cliente_pct and socio_pct:
        try:
            c = int(cliente_pct)
            s = int(socio_pct)
            if c + s == 100:
                divisao_lucro_venda = {"cliente_percentual": c, "socio_percentual": s}
        except (ValueError, TypeError):
            pass

    itens = []
    itens_json_str = request.POST.get("itens_json", "").strip()
    if itens_json_str:
        try:
            itens_data = json.loads(itens_json_str)
            for item in itens_data:
                pid = (item.get("produto_id") or "").strip()
                nome = (item.get("produto") or "").strip()
                try:
                    peso = float(str(item.get("peso_vendido_kg", 0)).replace(",", "."))
                    preco = float(str(item.get("preco_venda_kg", 0)).replace(",", "."))
                except (ValueError, TypeError):
                    peso = 0
                    preco = 0
                if pid and peso > 0:
                    itens.append({
                        "produto_id": pid,
                        "produto": nome,
                        "peso_vendido_kg": peso,
                        "preco_venda_kg": preco,
                    })
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
    if not itens:
        produto_ids = request.POST.getlist("produto_id")
        produtos_nomes = request.POST.getlist("produto_nome")
        pesos = request.POST.getlist("peso_vendido_kg")
        precos = request.POST.getlist("preco_venda_kg")
        for i in range(max(len(produto_ids), len(pesos), len(precos))):
            pid = produto_ids[i] if i < len(produto_ids) else ""
            nome = produtos_nomes[i] if i < len(produtos_nomes) else ""
            peso_str = (pesos[i] if i < len(pesos) else "0").replace(",", ".")
            preco_str = (precos[i] if i < len(precos) else "0").replace(",", ".")
            if not pid:
                continue
            try:
                peso = float(peso_str)
                preco = float(preco_str)
            except (ValueError, TypeError):
                continue
            if peso > 0:
                itens.append({
                    "produto_id": pid,
                    "produto": nome,
                    "peso_vendido_kg": peso,
                    "preco_venda_kg": preco,
                })

    def _ctx_nova(produtos_list):
        produtos_ctx = []
        for p in produtos_list:
            try:
                peso = float(p.get("peso_disponivel_kg") or 0)
                custo = float(p.get("custo_kg") or 0)
            except (TypeError, ValueError):
                peso = 0.0
                custo = 0.0
            produtos_ctx.append({
                "id": str(p.get("id", "")),
                "produto": str(p.get("produto", "")),
                "peso_disponivel_kg": peso,
                "custo_kg": custo,
            })
        return {
            "produtos": produtos_ctx,
            "hoje": hoje,
            "divisao_padrao": divisao_padrao,
        }

    if not data_venda:
        messages.error(request, "Informe a data da venda.")
        return render(request, "estoque_app/vendas_processados/nova.html", _ctx_nova(listar_disponiveis()))
    if not itens:
        messages.error(request, "Adicione ao menos um item à venda.")
        return render(request, "estoque_app/vendas_processados/nova.html", _ctx_nova(listar_disponiveis()))

    try:
        criar_venda_processado(
            data_venda=data_venda,
            tipo_venda=tipo_venda,
            itens=itens,
            divisao_lucro_venda=divisao_lucro_venda,
        )
        messages.success(request, "Venda registrada com sucesso.")
        return redirect("estoque_app:venda_processado_list")
    except ValueError as e:
        messages.error(request, str(e))
        return render(request, "estoque_app/vendas_processados/nova.html", _ctx_nova(listar_disponiveis()))
    except Exception as e:
        messages.error(request, f"Erro ao salvar: {e}")
        return render(request, "estoque_app/vendas_processados/nova.html", _ctx_nova(listar_disponiveis()))
