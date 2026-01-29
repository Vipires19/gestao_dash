"""
Views de categorias.

Localização: estoque_app/views/categoria_views.py

Views simples que chamam services e renderizam templates.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from estoque_app.services.categoria_service import CategoriaService


def categoria_list(request):
    """
    Lista todas as categorias.
    
    Rota: /categorias/
    """
    try:
        service = CategoriaService()
        categorias = service.listar_categorias()
        
        # Normaliza _id para id (Django não permite _id nos templates)
        for categoria in categorias:
            categoria['id'] = categoria.get('_id', '')
        
        context = {
            'categorias': categorias,
            'page_title': 'Categorias - Estoque'
        }
        
        return render(request, 'estoque_app/categorias/list.html', context)
    
    except Exception as e:
        messages.error(request, f'Erro ao listar categorias: {str(e)}')
        return render(request, 'estoque_app/categorias/list.html', {
            'categorias': [],
            'page_title': 'Categorias - Estoque'
        })


def categoria_create(request):
    """
    Cria uma nova categoria.
    
    GET: Exibe formulário
    POST: Cria categoria e redireciona para listagem
    
    Rota: /categorias/nova/
    """
    if request.method == 'POST':
        try:
            service = CategoriaService()
            
            # Obtém dados do formulário
            nome = request.POST.get('nome', '').strip()
            
            # Validações básicas
            if not nome:
                messages.error(request, 'Nome é obrigatório')
                return render(request, 'estoque_app/categorias/form.html', {
                    'page_title': 'Nova Categoria - Estoque',
                    'form_data': request.POST
                })
            
            # Cria categoria
            service.criar_categoria(nome=nome)
            
            messages.success(request, f'Categoria "{nome}" cadastrada com sucesso!')
            return redirect('estoque_app:categoria_list')
        
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, 'estoque_app/categorias/form.html', {
                'page_title': 'Nova Categoria - Estoque',
                'form_data': request.POST
            })
        
        except Exception as e:
            messages.error(request, f'Erro ao cadastrar categoria: {str(e)}')
            return render(request, 'estoque_app/categorias/form.html', {
                'page_title': 'Nova Categoria - Estoque',
                'form_data': request.POST
            })
    
    # GET: Exibe formulário
    return render(request, 'estoque_app/categorias/form.html', {
        'page_title': 'Nova Categoria - Estoque'
    })


def categoria_edit(request, categoria_id):
    """
    Edita uma categoria existente.
    
    GET: Exibe formulário preenchido
    POST: Atualiza categoria e redireciona para listagem
    
    Rota: /categorias/<id>/editar/
    """
    service = CategoriaService()
    
    if request.method == 'POST':
        try:
            # Obtém dados do formulário
            nome = request.POST.get('nome', '').strip()
            
            # Validações básicas
            if not nome:
                messages.error(request, 'Nome é obrigatório')
                categoria = service.buscar_categoria_por_id(categoria_id)
                if not categoria:
                    messages.error(request, 'Categoria não encontrada')
                    return redirect('estoque_app:categoria_list')
                # Normaliza _id para id
                categoria['id'] = categoria.get('_id', '')
                return render(request, 'estoque_app/categorias/form.html', {
                    'page_title': 'Editar Categoria - Estoque',
                    'categoria': categoria,
                    'form_data': request.POST
                })
            
            # Atualiza categoria
            categoria = service.atualizar_categoria(categoria_id, nome=nome)
            
            messages.success(request, f'Categoria "{nome}" atualizada com sucesso!')
            return redirect('estoque_app:categoria_list')
        
        except ValueError as e:
            messages.error(request, str(e))
            categoria = service.buscar_categoria_por_id(categoria_id)
            if not categoria:
                messages.error(request, 'Categoria não encontrada')
                return redirect('estoque_app:categoria_list')
            # Normaliza _id para id
            categoria['id'] = categoria.get('_id', '')
            return render(request, 'estoque_app/categorias/form.html', {
                'page_title': 'Editar Categoria - Estoque',
                'categoria': categoria,
                'form_data': request.POST
            })
        
        except Exception as e:
            messages.error(request, f'Erro ao atualizar categoria: {str(e)}')
            categoria = service.buscar_categoria_por_id(categoria_id)
            if not categoria:
                messages.error(request, 'Categoria não encontrada')
                return redirect('estoque_app:categoria_list')
            # Normaliza _id para id
            categoria['id'] = categoria.get('_id', '')
            return render(request, 'estoque_app/categorias/form.html', {
                'page_title': 'Editar Categoria - Estoque',
                'categoria': categoria,
                'form_data': request.POST
            })
    
    # GET: Exibe formulário preenchido
    categoria = service.buscar_categoria_por_id(categoria_id)
    
    if not categoria:
        messages.error(request, 'Categoria não encontrada')
        return redirect('estoque_app:categoria_list')
    
    # Normaliza _id para id
    categoria['id'] = categoria.get('_id', '')
    
    return render(request, 'estoque_app/categorias/form.html', {
        'page_title': 'Editar Categoria - Estoque',
        'categoria': categoria
    })
