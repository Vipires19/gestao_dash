"""
Views para vendas de caixas (Emporium Prime).
Nova venda de caixas por código; busca caixa por codigo_caixa.
"""
import json
from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse

from estoque_app.services.configuracao_service import obter_divisao_lucro_padrao
from estoque_app.services.caixa_estoque_service import obter_caixa_por_codigo
from estoque_app.services.venda_caixa_service import criar_venda_caixa, listar_vendas_caixas
from estoque_app.services.precificacao_service import obter_preco_ativo


def caixa_por_codigo_api(request):
    """API: GET ?codigo=CX-0001 retorna JSON da caixa EM_ESTOQUE ou erro."""
    codigo = (request.GET.get("codigo") or "").strip()
    if not codigo:
        return JsonResponse({"erro": "Informe o código da caixa."}, status=400)
    caixa = obter_caixa_por_codigo(codigo, apenas_em_estoque=True)
    if not caixa:
        return JsonResponse({"erro": "Caixa não encontrada ou não disponível para venda."}, status=404)
    produto_base = caixa.get("produto_base", "")
    valor_kg_custo = float(caixa.get("valor_kg") or 0)
    valor_venda_sugerido = obter_preco_ativo(produto_base, "CAIXA")
    valor_venda_kg = float(valor_venda_sugerido) if valor_venda_sugerido is not None else valor_kg_custo
    return JsonResponse({
        "id": caixa.get("id", ""),
        "codigo_caixa": caixa.get("codigo_caixa", ""),
        "produto_base": produto_base,
        "peso_atual_kg": float(caixa.get("peso_atual_kg") or 0),
        "valor_kg": valor_kg_custo,
        "valor_venda_kg": valor_venda_kg,
    })


def venda_caixa_nova(request):
    """Nova venda de caixas. GET: formulário; POST: registra venda."""
    hoje = date.today().isoformat()
    divisao_padrao = obter_divisao_lucro_padrao()

    if request.method == "POST":
        return _venda_caixa_create_post(request, hoje, divisao_padrao)

    return render(request, "estoque_app/vendas_caixas/nova.html", {
        "hoje": hoje,
        "divisao_padrao": divisao_padrao,
    })


def _venda_caixa_create_post(request, hoje, divisao_padrao):
    data_venda = request.POST.get("data_venda", "").strip()
    tipo_venda = (request.POST.get("tipo_venda") or "PROPRIA").strip()
    if tipo_venda not in ("PROPRIA", "PARCERIA"):
        tipo_venda = "PROPRIA"

    cliente_pct = request.POST.get("divisao_cliente_percentual", "").strip()
    socio_pct = request.POST.get("divisao_socio_percentual", "").strip()
    divisao_lucro_venda = None
    if cliente_pct and socio_pct:
        try:
            c, s = int(cliente_pct), int(socio_pct)
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
                caixa_id = (item.get("caixa_id") or "").strip()
                codigo = (item.get("codigo_caixa") or "").strip()
                produto_base = (item.get("produto_base") or "").strip()
                try:
                    peso = float(str(item.get("peso_kg", 0)).replace(",", "."))
                    custo_kg = float(str(item.get("custo_kg", 0)).replace(",", "."))
                    valor_venda_kg = float(str(item.get("valor_venda_kg", 0)).replace(",", "."))
                except (ValueError, TypeError):
                    continue
                if caixa_id and peso > 0:
                    itens.append({
                        "caixa_id": caixa_id,
                        "codigo_caixa": codigo,
                        "produto_base": produto_base,
                        "peso_kg": peso,
                        "custo_kg": custo_kg,
                        "valor_venda_kg": valor_venda_kg,
                    })
        except (ValueError, TypeError, json.JSONDecodeError):
            pass

    if not data_venda:
        messages.error(request, "Informe a data da venda.")
        return render(request, "estoque_app/vendas_caixas/nova.html", {
            "hoje": hoje,
            "divisao_padrao": divisao_padrao,
        })
    if not itens:
        messages.error(request, "Adicione ao menos uma caixa à venda.")
        return render(request, "estoque_app/vendas_caixas/nova.html", {
            "hoje": hoje,
            "divisao_padrao": divisao_padrao,
        })

    try:
        criar_venda_caixa(
            data_venda=data_venda,
            tipo_venda=tipo_venda,
            itens=itens,
            divisao_lucro_venda=divisao_lucro_venda,
        )
        messages.success(request, "Venda de caixas registrada com sucesso.")
        return redirect("estoque_app:venda_caixa_list")
    except ValueError as e:
        messages.error(request, str(e))
        return render(request, "estoque_app/vendas_caixas/nova.html", {
            "hoje": hoje,
            "divisao_padrao": divisao_padrao,
        })
    except Exception as e:
        messages.error(request, f"Erro ao salvar: {e}")
        return render(request, "estoque_app/vendas_caixas/nova.html", {
            "hoje": hoje,
            "divisao_padrao": divisao_padrao,
        })


def venda_caixa_list(request):
    """Listagem de vendas de caixas."""
    try:
        vendas = listar_vendas_caixas()
    except Exception as e:
        messages.error(request, f"Erro ao listar: {e}")
        vendas = []
    return render(request, "estoque_app/vendas_caixas/list.html", {"vendas": vendas})
