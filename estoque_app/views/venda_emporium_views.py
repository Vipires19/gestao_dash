"""
View para histórico unificado de vendas do Emporium Prime.
Lista vendas de processados e vendas de caixas (atacado) em uma única listagem.
Inclui geração de comprovante PDF unificado.
"""
from datetime import datetime
from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.contrib import messages

from estoque_app.services.venda_processado_service import (
    listar_vendas_processados,
    obter_venda_processado_por_id,
)
from estoque_app.services.venda_caixa_service import (
    listar_vendas_caixas,
    obter_venda_caixa_por_id,
)
from estoque_app.services.comprovante_service import gerar_comprovante_emporium_pdf


def _sort_key(item):
    """Ordenação por data_venda desc, created_at desc."""
    dv = item.get("data_venda")
    ct = item.get("created_at")
    d = dv if (dv and hasattr(dv, "year")) else datetime.min
    c = ct if (ct and hasattr(ct, "year")) else datetime.min
    return (d, c)


def venda_emporium_historico(request):
    """
    Histórico único: vendas de processados + vendas de caixas (atacado).
    Cada registro exibe: tipo (PROCESSADO/ATACADO), data, valor total, tipo de venda (PROPRIA/PARCERIA).
    """
    try:
        processados = listar_vendas_processados()
        caixas = listar_vendas_caixas()
    except Exception as e:
        messages.error(request, f"Erro ao carregar histórico: {e}")
        processados = []
        caixas = []

    for v in processados:
        v["tipo_emporium"] = "PROCESSADO"
    for v in caixas:
        v["tipo_emporium"] = "ATACADO"

    vendas = processados + caixas
    vendas.sort(key=_sort_key, reverse=True)

    return render(request, "estoque_app/vendas_emporium/historico.html", {"vendas": vendas})


def _normalizar_venda_para_comprovante(doc, tipo_label: str):
    """Normaliza documento de venda (processado ou caixa) para o formato do comprovante PDF."""
    itens = doc.get("itens", [])
    if tipo_label == "Processados":
        itens_norm = [
            {
                "nome": (item.get("produto") or "").strip(),
                "quantidade": f"{float(item.get('peso_vendido_kg') or 0):.3f} kg",
                "valor_unitario": float(item.get("preco_venda_kg") or 0),
                "valor_total": float(item.get("valor_total_venda") or 0),
            }
            for item in itens
        ]
    else:
        itens_norm = [
            {
                "nome": (item.get("produto_base") or item.get("codigo_caixa") or "").strip(),
                "quantidade": f"{float(item.get('peso_kg') or 0):.3f} kg",
                "valor_unitario": float(item.get("valor_venda_kg") or 0),
                "valor_total": float(item.get("valor_venda_item") or 0),
            }
            for item in itens
        ]
    return {
        "numero_venda": doc.get("id", ""),
        "data_venda": doc.get("data_venda"),
        "tipo_venda_label": tipo_label,
        "itens": itens_norm,
        "valor_total_venda": float(doc.get("valor_total_venda") or 0),
    }


def emporium_comprovante(request, venda_id):
    """
    Gera e retorna o comprovante PDF da venda Emporium Prime (processados ou atacado).
    Rota: /emporium/vendas/<id>/comprovante/
    """
    venda_processado = obter_venda_processado_por_id(venda_id)
    if venda_processado:
        venda_norm = _normalizar_venda_para_comprovante(venda_processado, "Processados")
    else:
        venda_caixa = obter_venda_caixa_por_id(venda_id)
        if not venda_caixa:
            raise Http404("Venda não encontrada.")
        venda_norm = _normalizar_venda_para_comprovante(venda_caixa, "Atacado")

    pdf_buffer = gerar_comprovante_emporium_pdf(venda_norm)
    response = HttpResponse(pdf_buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="comprovante_emporium_{venda_id}.pdf"'
    return response
