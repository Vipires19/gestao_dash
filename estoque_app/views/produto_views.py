"""
Views de produtos.

Localização: estoque_app/views/produto_views.py

Views simples que chamam services e renderizam templates.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from estoque_app.services.produto_service import ProdutoService
from estoque_app.services.categoria_service import CategoriaService


def produto_list(request):
    """
    Lista todos os produtos.
    
    Rota: /produtos/
    """
    try:
        produto_service = ProdutoService()
        produtos = produto_service.listar_produtos()
        
        # Normaliza _id para id (Django não permite _id nos templates)
        for produto in produtos:
            produto['id'] = produto.get('_id', '')
        
        context = {
            'produtos': produtos,
            'page_title': 'Produtos - Estoque'
        }
        
        return render(request, 'estoque_app/produtos/list.html', context)
    
    except Exception as e:
        messages.error(request, f'Erro ao listar produtos: {str(e)}')
        return render(request, 'estoque_app/produtos/list.html', {
            'produtos': [],
            'page_title': 'Produtos - Estoque'
        })


def produto_create(request):
    """
    Cria um novo produto.
    
    GET: Exibe formulário
    POST: Cria produto e redireciona para listagem
    
    Rota: /produtos/novo/
    """
    categoria_service = CategoriaService()
    
    if request.method == 'POST':
        try:
            produto_service = ProdutoService()
            
            # Obtém dados do formulário
            codigo = request.POST.get('codigo', '').strip()
            nome = request.POST.get('nome', '').strip()
            categoria_id = request.POST.get('categoria_id', '').strip()
            preco_compra = request.POST.get('preco_compra', '0')
            preco_venda = request.POST.get('preco_venda', '0')
            quantidade = request.POST.get('quantidade', '0')
            
            # Validações básicas
            if not codigo:
                messages.error(request, 'Código é obrigatório')
                categorias = categoria_service.listar_categorias()
                # Normaliza _id para id
                for categoria in categorias:
                    categoria['id'] = categoria.get('_id', '')
                return render(request, 'estoque_app/produtos/form.html', {
                    'page_title': 'Novo Produto - Estoque',
                    'categorias': categorias,
                    'form_data': request.POST
                })
            
            if not nome:
                messages.error(request, 'Nome é obrigatório')
                categorias = categoria_service.listar_categorias()
                # Normaliza _id para id
                for categoria in categorias:
                    categoria['id'] = categoria.get('_id', '')
                return render(request, 'estoque_app/produtos/form.html', {
                    'page_title': 'Novo Produto - Estoque',
                    'categorias': categorias,
                    'form_data': request.POST
                })
            
            if not categoria_id:
                messages.error(request, 'Categoria é obrigatória')
                categorias = categoria_service.listar_categorias()
                # Normaliza _id para id
                for categoria in categorias:
                    categoria['id'] = categoria.get('_id', '')
                return render(request, 'estoque_app/produtos/form.html', {
                    'page_title': 'Novo Produto - Estoque',
                    'categorias': categorias,
                    'form_data': request.POST
                })
            
            # Converte valores
            try:
                preco_compra = float(preco_compra)
                preco_venda = float(preco_venda)
                quantidade = int(quantidade)
            except ValueError:
                messages.error(request, 'Valores inválidos')
                categorias = categoria_service.listar_categorias()
                # Normaliza _id para id
                for categoria in categorias:
                    categoria['id'] = categoria.get('_id', '')
                return render(request, 'estoque_app/produtos/form.html', {
                    'page_title': 'Novo Produto - Estoque',
                    'categorias': categorias,
                    'form_data': request.POST
                })
            
            # Cria produto
            produto_service.criar_produto(
                codigo=codigo,
                nome=nome,
                categoria_id=categoria_id,
                preco_compra=preco_compra,
                preco_venda=preco_venda,
                quantidade=quantidade
            )
            
            messages.success(request, f'Produto "{nome}" cadastrado com sucesso!')
            return redirect('estoque_app:produto_list')
        
        except ValueError as e:
            messages.error(request, str(e))
            categorias = categoria_service.listar_categorias()
            # Normaliza _id para id
            for categoria in categorias:
                categoria['id'] = categoria.get('_id', '')
            return render(request, 'estoque_app/produtos/form.html', {
                'page_title': 'Novo Produto - Estoque',
                'categorias': categorias,
                'form_data': request.POST
            })
        
        except Exception as e:
            messages.error(request, f'Erro ao cadastrar produto: {str(e)}')
            categorias = categoria_service.listar_categorias()
            # Normaliza _id para id
            for categoria in categorias:
                categoria['id'] = categoria.get('_id', '')
            return render(request, 'estoque_app/produtos/form.html', {
                'page_title': 'Novo Produto - Estoque',
                'categorias': categorias,
                'form_data': request.POST
            })
    
    # GET: Exibe formulário
    categorias = categoria_service.listar_categorias()
    # Normaliza _id para id (Django não permite _id nos templates)
    for categoria in categorias:
        categoria['id'] = categoria.get('_id', '')
    
    return render(request, 'estoque_app/produtos/form.html', {
        'page_title': 'Novo Produto - Estoque',
        'categorias': categorias
    })


def produto_edit(request, produto_id):
    """
    Edita um produto existente.
    
    GET: Exibe formulário preenchido
    POST: Atualiza produto e redireciona para listagem
    
    Rota: /produtos/<id>/editar/
    """
    produto_service = ProdutoService()
    categoria_service = CategoriaService()
    
    if request.method == 'POST':
        try:
            # Obtém dados do formulário
            codigo = request.POST.get('codigo', '').strip()
            nome = request.POST.get('nome', '').strip()
            categoria_id = request.POST.get('categoria_id', '').strip()
            preco_compra = request.POST.get('preco_compra', '0')
            preco_venda = request.POST.get('preco_venda', '0')
            quantidade = request.POST.get('quantidade', '0')
            
            # Validações básicas
            if not codigo:
                messages.error(request, 'Código é obrigatório')
                produto = produto_service.obter_produto_por_id(produto_id)
                if not produto:
                    messages.error(request, 'Produto não encontrado')
                    return redirect('estoque_app:produto_list')
                categorias = categoria_service.listar_categorias()
                # Normaliza _id para id
                for categoria in categorias:
                    categoria['id'] = categoria.get('_id', '')
                produto['id'] = produto.get('_id', '')
                return render(request, 'estoque_app/produtos/form.html', {
                    'page_title': 'Editar Produto - Estoque',
                    'produto': produto,
                    'categorias': categorias,
                    'form_data': request.POST
                })
            
            if not nome:
                messages.error(request, 'Nome é obrigatório')
                produto = produto_service.obter_produto_por_id(produto_id)
                if not produto:
                    messages.error(request, 'Produto não encontrado')
                    return redirect('estoque_app:produto_list')
                categorias = categoria_service.listar_categorias()
                # Normaliza _id para id
                for categoria in categorias:
                    categoria['id'] = categoria.get('_id', '')
                produto['id'] = produto.get('_id', '')
                return render(request, 'estoque_app/produtos/form.html', {
                    'page_title': 'Editar Produto - Estoque',
                    'produto': produto,
                    'categorias': categorias,
                    'form_data': request.POST
                })
            
            if not categoria_id:
                messages.error(request, 'Categoria é obrigatória')
                produto = produto_service.obter_produto_por_id(produto_id)
                if not produto:
                    messages.error(request, 'Produto não encontrado')
                    return redirect('estoque_app:produto_list')
                categorias = categoria_service.listar_categorias()
                # Normaliza _id para id
                for categoria in categorias:
                    categoria['id'] = categoria.get('_id', '')
                produto['id'] = produto.get('_id', '')
                return render(request, 'estoque_app/produtos/form.html', {
                    'page_title': 'Editar Produto - Estoque',
                    'produto': produto,
                    'categorias': categorias,
                    'form_data': request.POST
                })
            
            # Converte valores
            try:
                preco_compra = float(preco_compra)
                preco_venda = float(preco_venda)
                quantidade = int(quantidade)
            except ValueError:
                messages.error(request, 'Valores inválidos')
                produto = produto_service.obter_produto_por_id(produto_id)
                if not produto:
                    messages.error(request, 'Produto não encontrado')
                    return redirect('estoque_app:produto_list')
                categorias = categoria_service.listar_categorias()
                # Normaliza _id para id
                for categoria in categorias:
                    categoria['id'] = categoria.get('_id', '')
                produto['id'] = produto.get('_id', '')
                return render(request, 'estoque_app/produtos/form.html', {
                    'page_title': 'Editar Produto - Estoque',
                    'produto': produto,
                    'categorias': categorias,
                    'form_data': request.POST
                })
            
            # Atualiza produto
            produto_service.atualizar_produto(
                produto_id=produto_id,
                codigo=codigo,
                nome=nome,
                categoria_id=categoria_id,
                preco_compra=preco_compra,
                preco_venda=preco_venda,
                quantidade=quantidade
            )
            
            messages.success(request, f'Produto "{nome}" atualizado com sucesso!')
            return redirect('estoque_app:produto_list')
        
        except ValueError as e:
            messages.error(request, str(e))
            produto = produto_service.obter_produto_por_id(produto_id)
            if not produto:
                messages.error(request, 'Produto não encontrado')
                return redirect('estoque_app:produto_list')
            categorias = categoria_service.listar_categorias()
            # Normaliza _id para id
            for categoria in categorias:
                categoria['id'] = categoria.get('_id', '')
            produto['id'] = produto.get('_id', '')
            return render(request, 'estoque_app/produtos/form.html', {
                'page_title': 'Editar Produto - Estoque',
                'produto': produto,
                'categorias': categorias,
                'form_data': request.POST
            })
        
        except Exception as e:
            messages.error(request, f'Erro ao atualizar produto: {str(e)}')
            produto = produto_service.obter_produto_por_id(produto_id)
            if not produto:
                messages.error(request, 'Produto não encontrado')
                return redirect('estoque_app:produto_list')
            categorias = categoria_service.listar_categorias()
            # Normaliza _id para id
            for categoria in categorias:
                categoria['id'] = categoria.get('_id', '')
            produto['id'] = produto.get('_id', '')
            return render(request, 'estoque_app/produtos/form.html', {
                'page_title': 'Editar Produto - Estoque',
                'produto': produto,
                'categorias': categorias,
                'form_data': request.POST
            })
    
    # GET: Exibe formulário preenchido
    produto = produto_service.obter_produto_por_id(produto_id)
    
    if not produto:
        messages.error(request, 'Produto não encontrado')
        return redirect('estoque_app:produto_list')
    
    categorias = categoria_service.listar_categorias()
    # Normaliza _id para id
    for categoria in categorias:
        categoria['id'] = categoria.get('_id', '')
    produto['id'] = produto.get('_id', '')
    
    return render(request, 'estoque_app/produtos/form.html', {
        'page_title': 'Editar Produto - Estoque',
        'produto': produto,
        'categorias': categorias
    })
