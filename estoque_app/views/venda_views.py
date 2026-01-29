"""
Views de vendas.

Localização: estoque_app/views/venda_views.py

Views simples que chamam services e renderizam templates.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder
from estoque_app.services.venda_service import VendaService
from estoque_app.services.comprovante_service import gerar_comprovante_pdf
import json
from datetime import datetime


@csrf_exempt
def venda_nova(request):
    """
    Tela de nova venda (PDV).
    
    GET: Exibe formulário de venda
    POST: Processa busca de produto (via AJAX)
    
    Rota: /vendas/nova/
    """
    if request.method == 'POST':
        # Processa busca de produto (chamada AJAX)
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                acao = data.get('acao')
                
                if acao == 'buscar_produto':
                    codigo = data.get('codigo', '').strip()
                    
                    if not codigo:
                        return JsonResponse({'erro': 'Código é obrigatório'}, status=400)
                    
                    service = VendaService()
                    produto = service.buscar_produto_por_codigo(codigo)
                    
                    if produto:
                        return JsonResponse(produto)
                    else:
                        return JsonResponse({'erro': 'Produto não encontrado'}, status=404)
                
                elif acao == 'finalizar_venda':
                    itens = data.get('itens', [])
                    
                    if not itens or len(itens) == 0:
                        return JsonResponse({'erro': 'A venda deve conter pelo menos um item'}, status=400)
                    
                    service = VendaService()
                    venda = service.registrar_venda(itens)
                    
                    return JsonResponse({
                        'sucesso': True,
                        'venda_id': venda['_id'],
                        'mensagem': 'Venda registrada com sucesso!'
                    })
                
            except ValueError as e:
                return JsonResponse({'erro': str(e)}, status=400)
            except Exception as e:
                return JsonResponse({'erro': f'Erro ao processar: {str(e)}'}, status=500)
    
    # GET: Exibe formulário
    return render(request, 'estoque_app/vendas/nova.html', {
        'page_title': 'Nova Venda - PDV'
    })


def venda_confirmacao(request, venda_id):
    """
    Página de confirmação da venda.
    
    Rota: /vendas/<id>/confirmacao/
    """
    service = VendaService()
    venda = service.obter_venda_por_id(venda_id)
    
    if not venda:
        messages.error(request, 'Venda não encontrada')
        return redirect('estoque_app:venda_nova')
    
    return render(request, 'estoque_app/vendas/confirmacao.html', {
        'page_title': 'Venda Registrada',
        'venda': venda
    })


def venda_list(request):
    """
    Lista todas as vendas.
    
    GET → lista vendas
    
    Rota: /vendas/
    """
    try:
        service = VendaService()
        vendas = service.listar_vendas()
        
        return render(request, 'estoque_app/vendas/list.html', {
            'vendas': vendas,
            'page_title': 'Vendas'
        })
    except Exception as e:
        messages.error(request, f'Erro ao listar vendas: {str(e)}')
        return render(request, 'estoque_app/vendas/list.html', {
            'vendas': [],
            'page_title': 'Vendas'
        })


def venda_detail(request, venda_id):
    """
    Detalhe de uma venda.
    
    GET → exibe detalhe da venda
    
    Rota: /vendas/<id>/
    """
    service = VendaService()
    venda = service.obter_venda_por_id(venda_id)
    
    if not venda:
        messages.error(request, 'Venda não encontrada')
        return redirect('estoque_app:venda_list')
    
    return render(request, 'estoque_app/vendas/detail.html', {
        'page_title': 'Detalhe da Venda',
        'venda': venda
    })


def venda_comprovante(request, venda_id):
    """
    Gera e retorna o comprovante PDF da venda.
    
    Rota: /vendas/<id>/comprovante/
    """
    service = VendaService()
    venda = service.obter_venda_por_id(venda_id)
    
    if not venda:
        return HttpResponse('Venda não encontrada', status=404)
    
    # Gera o PDF
    pdf_buffer = gerar_comprovante_pdf(venda)
    
    # Prepara resposta
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="comprovante_venda_{venda_id}.pdf"'
    
    return response
