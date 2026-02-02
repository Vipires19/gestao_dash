"""
Views do módulo Precificação (Emporium Prime).
Produto comercial = produto_base + tipo (CAIXA | PROCESSADO) + nome_comercial.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse

from estoque_app.services.precificacao_service import (
    listar_produtos_base_caixa,
    listar_produtos_base_processado,
    analise_estoque,
    obter_preco_ativo,
    listar_precificacoes_completo,
    salvar_precificacao,
    classificar_margem,
    listar_precificacoes_ativas,
)
from estoque_app.services.comprovante_service import gerar_tabela_precos_pdf


def precificacao_list(request):
    """Listagem de precificações ativas. Rota: /precificacao/emporium/"""
    try:
        precificacoes = listar_precificacoes_completo()
    except Exception as e:
        messages.error(request, f"Erro ao listar: {e}")
        precificacoes = []
    return render(request, "estoque_app/precificacao/list.html", {"precificacoes": precificacoes})


def precificacao_nova(request):
    """
    Nova precificação. GET: form com produto_base (por tipo), tipo, nome_comercial, margem ou preço.
    POST: salva e redireciona para listagem.
    """
    if request.method == "POST":
        return _precificacao_salvar(request)

    produto_base = request.GET.get("produto_base", "").strip()
    tipo = request.GET.get("tipo", "CAIXA").strip().upper()
    if tipo not in ("CAIXA", "PROCESSADO"):
        tipo = "CAIXA"

    produtos_caixa = listar_produtos_base_caixa()
    produtos_processado = listar_produtos_base_processado()

    analise = None
    nome_comercial_sugerido = produto_base or ""
    if nome_comercial_sugerido and tipo == "CAIXA":
        nome_comercial_sugerido = f"{produto_base} – Caixa"
    elif nome_comercial_sugerido and tipo == "PROCESSADO":
        nome_comercial_sugerido = f"{produto_base} – Processado"

    if produto_base:
        try:
            analise = analise_estoque(produto_base, tipo)
        except Exception as e:
            messages.error(request, f"Erro na análise: {e}")
            analise = {
                "custo_medio_ponderado_kg": 0,
                "perda_media_percentual": 0,
                "custo_real_kg": 0,
                "quantidade_estoque_kg": 0,
                "qtd_itens": 0,
            }

    return render(request, "estoque_app/precificacao/nova.html", {
        "produtos_caixa": produtos_caixa,
        "produtos_processado": produtos_processado,
        "produto_base_selecionado": produto_base,
        "tipo_selecionado": tipo,
        "analise": analise,
        "nome_comercial_sugerido": nome_comercial_sugerido,
    })


def _precificacao_salvar(request):
    produto_base = request.POST.get("produto_base", "").strip()
    tipo = (request.POST.get("tipo", "CAIXA") or "").strip().upper()
    if tipo not in ("CAIXA", "PROCESSADO"):
        tipo = "CAIXA"
    nome_comercial = (request.POST.get("nome_comercial", "") or "").strip() or f"{produto_base} – {tipo}"

    preco_str = (request.POST.get("preco_venda_kg", "") or "").strip().replace(",", ".")
    margem_str = (request.POST.get("margem_percentual", "") or "").strip().replace(",", ".")

    if not produto_base:
        messages.error(request, "Selecione o produto base.")
        return redirect("estoque_app:precificacao_nova")

    try:
        analise = analise_estoque(produto_base, tipo)
    except Exception as e:
        messages.error(request, f"Erro na análise: {e}")
        return redirect("estoque_app:precificacao_nova")

    custo_real = analise.get("custo_real_kg", 0) or 0
    preco_venda_kg = None
    margem_percentual = None

    if preco_str:
        try:
            preco_venda_kg = float(preco_str)
        except ValueError:
            messages.error(request, "Preço de venda inválido.")
            return redirect("estoque_app:precificacao_nova")
    if margem_str:
        try:
            margem_percentual = float(margem_str)
            if preco_venda_kg is None and custo_real > 0:
                preco_venda_kg = round(custo_real * (1 + margem_percentual / 100), 2)
        except ValueError:
            pass

    if preco_venda_kg is None:
        preco_venda_kg = custo_real
    if preco_venda_kg < 0:
        messages.error(request, "Preço de venda deve ser positivo.")
        return redirect("estoque_app:precificacao_nova")

    try:
        salvar_precificacao(
            produto_base=produto_base,
            tipo=tipo,
            nome_comercial=nome_comercial,
            preco_venda_kg=preco_venda_kg,
            margem_percentual=margem_percentual,
            custo_real_kg=custo_real,
            custo_medio_ponderado_kg=analise.get("custo_medio_ponderado_kg", 0),
            perda_media_percentual=analise.get("perda_media_percentual", 0),
            quantidade_estoque_kg=analise.get("quantidade_estoque_kg", 0),
        )
        messages.success(request, "Precificação salva com sucesso.")
        return redirect("estoque_app:precificacao_list")
    except Exception as e:
        messages.error(request, f"Erro ao salvar: {e}")
        return redirect("estoque_app:precificacao_nova")


def precificacao_tabela_pdf(request):
    """Gera PDF da tabela de preços (produtos comerciais ativos)."""
    try:
        itens = listar_precificacoes_ativas()
    except Exception as e:
        return HttpResponse(f"Erro ao gerar PDF: {e}", status=500)
    pdf_buffer = gerar_tabela_precos_pdf(itens)
    response = HttpResponse(pdf_buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="tabela_precos_emporium.pdf"'
    return response
