"""
Views do módulo Operação (entradas de estoque, caixas, fornecedores).
"""
import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.http import FileResponse, Http404

from estoque_app.services.fornecedor_service import (
    listar_fornecedores,
    criar_fornecedor,
)
from estoque_app.services.entrada_estoque_service import (
    listar_entradas,
    obter_entrada_por_id,
    criar_entrada,
)
from estoque_app.services.caixa_estoque_service import (
    listar_caixas,
    obter_caixa_por_id,
)
from estoque_app.services.processamento_service import (
    listar_processamentos,
    criar_processamento,
)
from estoque_app.services.produto_derivado_service import (
    listar_disponiveis as listar_produtos_derivados,
    registrar_from_processamento as registrar_produtos_derivados,
)


def entrada_list(request):
    """Listagem de entradas de estoque. Rota: /operacao/entradas/"""
    try:
        entradas = listar_entradas()
    except Exception as e:
        messages.error(request, f"Erro ao listar entradas: {e}")
        entradas = []
    return render(request, "estoque_app/operacao/entradas/list.html", {"entradas": entradas})


def entrada_nova(request):
    """Formulário de nova entrada. GET: exibe form; POST: processa e redireciona."""
    fornecedores = listar_fornecedores()
    if request.method == "POST":
        return _entrada_create_post(request, fornecedores)
    from datetime import date
    hoje = date.today().isoformat()
    return render(request, "estoque_app/operacao/entradas/nova.html", {
        "fornecedores": fornecedores,
        "hoje": hoje,
    })


def _entrada_create_post(request, fornecedores):
    fornecedor_id = request.POST.get("fornecedor_id", "").strip()
    data_entrada = request.POST.get("data_entrada", "").strip()
    valor_total = request.POST.get("valor_total", "").strip().replace(",", ".")
    data_pagamento = request.POST.get("data_pagamento", "").strip() or None
    status_pagamento = request.POST.get("status_pagamento", "PENDENTE").strip()
    forma_pagamento = request.POST.get("forma_pagamento", "BOLETO").strip()
    nf_numero = request.POST.get("nf_numero", "").strip()
    observacoes = request.POST.get("observacoes", "").strip()
    # NF-e upload
    nf_arquivo_path = ""
    nf_file = request.FILES.get("nf_arquivo")
    if nf_file:
        try:
            media_root = getattr(settings, "MEDIA_ROOT", None)
            if media_root:
                nf_dir = os.path.join(media_root, "nf_entradas")
                os.makedirs(nf_dir, exist_ok=True)
                ext = os.path.splitext(nf_file.name)[1] or ".pdf"
                nome_salvo = f"nf_{nf_numero or 'sem_numero'}{ext}".replace(" ", "_")
                path_full = os.path.join(nf_dir, nome_salvo)
                with open(path_full, "wb") as f:
                    for chunk in nf_file.chunks():
                        f.write(chunk)
                nf_arquivo_path = f"nf_entradas/{nome_salvo}"
        except Exception as e:
            messages.warning(request, f"Arquivo NF-e não salvo: {e}")
    # Produtos: listas paralelas
    produtos_base = request.POST.getlist("produto_base")
    qtd_caixas = request.POST.getlist("quantidade_caixas")
    peso_caixa = request.POST.getlist("peso_por_caixa_kg")
    valor_produto = request.POST.getlist("valor_total_produto")
    produtos = []
    for i in range(max(len(produtos_base), len(qtd_caixas), len(peso_caixa), len(valor_produto))):
        pb = (produtos_base[i] if i < len(produtos_base) else "").strip()
        qtd = int(qtd_caixas[i]) if i < len(qtd_caixas) else 0
        peso = (peso_caixa[i] if i < len(peso_caixa) else "0").replace(",", ".")
        valor = (valor_produto[i] if i < len(valor_produto) else "0").replace(",", ".")
        if pb and qtd > 0 and float(peso) > 0:
            try:
                produtos.append({
                    "produto_base": pb,
                    "quantidade_caixas": qtd,
                    "peso_por_caixa_kg": float(peso),
                    "valor_total_produto": float(valor),
                })
            except (ValueError, TypeError):
                pass
    try:
        valor_f = float(valor_total) if valor_total else 0
    except ValueError:
        valor_f = 0
    if not fornecedor_id:
        messages.error(request, "Selecione o fornecedor.")
        return render(request, "estoque_app/operacao/entradas/nova.html", {
            "fornecedores": fornecedores,
            "form_data": request.POST,
        })
    if not data_entrada:
        messages.error(request, "Informe a data da entrada.")
        return render(request, "estoque_app/operacao/entradas/nova.html", {
            "fornecedores": fornecedores,
            "form_data": request.POST,
        })
    if not produtos:
        messages.error(request, "Adicione ao menos um produto à entrada.")
        return render(request, "estoque_app/operacao/entradas/nova.html", {
            "fornecedores": fornecedores,
            "form_data": request.POST,
        })
    try:
        criar_entrada(
            fornecedor_id=fornecedor_id,
            data_entrada=data_entrada,
            valor_total=valor_f,
            data_pagamento=data_pagamento,
            status_pagamento=status_pagamento,
            forma_pagamento=forma_pagamento,
            parcelas=1,
            nf_numero=nf_numero,
            nf_arquivo=nf_arquivo_path,
            observacoes=observacoes,
            produtos=produtos,
        )
        messages.success(request, "Entrada de estoque registrada com sucesso.")
        return redirect("estoque_app:entrada_list")
    except ValueError as e:
        messages.error(request, str(e))
        return render(request, "estoque_app/operacao/entradas/nova.html", {
            "fornecedores": fornecedores,
            "form_data": request.POST,
        })
    except Exception as e:
        messages.error(request, f"Erro ao salvar: {e}")
        return render(request, "estoque_app/operacao/entradas/nova.html", {
            "fornecedores": fornecedores,
            "form_data": request.POST,
        })


def caixa_list(request):
    """Listagem de caixas com filtros. Rota: /operacao/caixas/"""
    produto = request.GET.get("produto", "").strip()
    fornecedor_id = request.GET.get("fornecedor_id", "").strip()
    status = request.GET.get("status", "").strip()
    try:
        caixas = listar_caixas(produto=produto or None, fornecedor_id=fornecedor_id or None, status=status or None)
    except Exception as e:
        messages.error(request, f"Erro ao listar caixas: {e}")
        caixas = []
    fornecedores = listar_fornecedores()
    return render(request, "estoque_app/operacao/caixas/list.html", {
        "caixas": caixas,
        "fornecedores": fornecedores,
        "filtro_produto": produto,
        "filtro_fornecedor_id": fornecedor_id,
        "filtro_status": status,
    })


def estoque_emporium(request):
    """
    Tela única Estoque Emporium Prime: caixas + produtos processados em blocos separados.
    Busca única filtra por: código (caixa ou produto), fornecedor, status (caixas).
    Rota: /operacao/estoque-emporium/
    """
    codigo = request.GET.get("codigo", "").strip()
    fornecedor_id = request.GET.get("fornecedor_id", "").strip()
    status = request.GET.get("status", "").strip()
    try:
        caixas = listar_caixas(
            codigo=codigo or None,
            fornecedor_id=fornecedor_id or None,
            status=status or None,
        )
    except Exception as e:
        messages.error(request, f"Erro ao listar caixas: {e}")
        caixas = []
    try:
        produtos_derivados = listar_produtos_derivados(produto=codigo or None)
    except Exception as e:
        messages.error(request, f"Erro ao listar produtos processados: {e}")
        produtos_derivados = []
    fornecedores = listar_fornecedores()
    return render(request, "estoque_app/operacao/estoque_emporium.html", {
        "caixas": caixas,
        "produtos_derivados": produtos_derivados,
        "fornecedores": fornecedores,
        "filtro_codigo": codigo,
        "filtro_fornecedor_id": fornecedor_id,
        "filtro_status": status,
    })


def caixa_detail(request, caixa_id):
    """Detalhe de uma caixa. Rota: /operacao/caixas/<id>/"""
    caixa = obter_caixa_por_id(caixa_id)
    if not caixa:
        raise Http404("Caixa não encontrada.")
    return render(request, "estoque_app/operacao/caixas/detail.html", {"caixa": caixa})


def caixa_nf_download(request, caixa_id):
    """Download do arquivo NF-e da entrada associada à caixa. Rota: /operacao/caixas/<id>/nf/"""
    caixa = obter_caixa_por_id(caixa_id)
    if not caixa or not caixa.get("nf_arquivo"):
        raise Http404("Arquivo não encontrado.")
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if not media_root:
        raise Http404("Arquivo não configurado.")
    path_full = os.path.join(media_root, caixa["nf_arquivo"])
    if not os.path.isfile(path_full):
        raise Http404("Arquivo não encontrado.")
    return FileResponse(open(path_full, "rb"), as_attachment=True, filename=os.path.basename(path_full))


def processamento_list(request):
    """Listagem de processamentos. Rota: /operacao/processamentos/"""
    try:
        processamentos = listar_processamentos()
    except Exception as e:
        messages.error(request, f"Erro ao listar processamentos: {e}")
        processamentos = []
    return render(request, "estoque_app/operacao/processamentos/list.html", {"processamentos": processamentos})


def processamento_novo(request):
    """Novo processamento. GET: exibe form com caixas EM_ESTOQUE; POST: valida e registra."""
    from datetime import date
    hoje = date.today().isoformat()

    if request.method == "POST":
        return _processamento_create_post(request, hoje)

    caixas = listar_caixas(status="EM_ESTOQUE")
    filtro_produto = request.GET.get("produto", "").strip()
    if filtro_produto:
        caixas = [c for c in caixas if filtro_produto.lower() in (c.get("produto_base") or "").lower()]
    return render(request, "estoque_app/operacao/processamentos/novo.html", {
        "caixas": caixas,
        "hoje": hoje,
        "filtro_produto": filtro_produto,
    })


def _processamento_create_post(request, hoje):
    data_processamento = request.POST.get("data_processamento", "").strip()
    selecionados = request.POST.getlist("selecionar")
    caixas_origem = []
    for caixa_id in selecionados:
        if not caixa_id:
            continue
        peso_str = (request.POST.get(f"peso_utilizado_{caixa_id}") or "0").replace(",", ".")
        produto_base = (request.POST.get(f"produto_base_{caixa_id}") or "").strip()
        try:
            peso_kg = float(peso_str)
        except (ValueError, TypeError):
            peso_kg = 0
        if peso_kg > 0:
            caixas_origem.append({
                "caixa_id": caixa_id,
                "produto_base": produto_base,
                "peso_utilizado_kg": peso_kg,
            })

    produtos_nomes = request.POST.getlist("produto_gerado")
    produtos_pesos = request.POST.getlist("peso_gerado_kg")
    produtos_gerados = []
    for i in range(max(len(produtos_nomes), len(produtos_pesos))):
        nome = (produtos_nomes[i] if i < len(produtos_nomes) else "").strip()
        peso_str = (produtos_pesos[i] if i < len(produtos_pesos) else "0").replace(",", ".")
        if not nome:
            continue
        try:
            peso_kg = float(peso_str)
        except (ValueError, TypeError):
            peso_kg = 0
        if peso_kg > 0:
            produtos_gerados.append({"produto": nome, "peso_kg": peso_kg})

    perda_str = (request.POST.get("perda_kg") or "0").replace(",", ".")
    try:
        perda_kg = float(perda_str)
    except (ValueError, TypeError):
        perda_kg = 0
    if perda_kg < 0:
        perda_kg = 0
    observacoes = request.POST.get("observacoes", "").strip()

    if not data_processamento:
        messages.error(request, "Informe a data do processamento.")
        caixas = listar_caixas(status="EM_ESTOQUE")
        return render(request, "estoque_app/operacao/processamentos/novo.html", {
            "caixas": caixas,
            "hoje": hoje,
            "filtro_produto": request.GET.get("produto", ""),
        })
    if not caixas_origem:
        messages.error(request, "Selecione ao menos uma caixa e informe o peso utilizado.")
        caixas = listar_caixas(status="EM_ESTOQUE")
        return render(request, "estoque_app/operacao/processamentos/novo.html", {
            "caixas": caixas,
            "hoje": hoje,
            "filtro_produto": request.GET.get("produto", ""),
        })
    if not produtos_gerados:
        messages.error(request, "Informe ao menos um produto gerado com peso.")
        caixas = listar_caixas(status="EM_ESTOQUE")
        return render(request, "estoque_app/operacao/processamentos/novo.html", {
            "caixas": caixas,
            "hoje": hoje,
            "filtro_produto": request.GET.get("produto", ""),
        })

    try:
        processamento_doc = criar_processamento(
            data_processamento=data_processamento,
            caixas_origem=caixas_origem,
            produtos_gerados=produtos_gerados,
            perda_kg=perda_kg,
            observacoes=observacoes,
        )
        registrar_produtos_derivados(processamento_doc)
        messages.success(request, "Processamento registrado com sucesso.")
        return redirect("estoque_app:processamento_list")
    except ValueError as e:
        messages.error(request, str(e))
        caixas = listar_caixas(status="EM_ESTOQUE")
        return render(request, "estoque_app/operacao/processamentos/novo.html", {
            "caixas": caixas,
            "hoje": hoje,
            "filtro_produto": request.GET.get("produto", ""),
        })
    except Exception as e:
        messages.error(request, f"Erro ao salvar: {e}")
        caixas = listar_caixas(status="EM_ESTOQUE")
        return render(request, "estoque_app/operacao/processamentos/novo.html", {
            "caixas": caixas,
            "hoje": hoje,
            "filtro_produto": request.GET.get("produto", ""),
        })


def fornecedor_list(request):
    """Listagem e cadastro de fornecedores. Rota: /operacao/fornecedores/"""
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        if nome:
            try:
                criar_fornecedor(nome)
                messages.success(request, "Fornecedor cadastrado.")
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Erro: {e}")
        else:
            messages.error(request, "Nome é obrigatório.")
        return redirect("estoque_app:fornecedor_list")
    fornecedores = listar_fornecedores()
    return render(request, "estoque_app/operacao/fornecedores/list.html", {"fornecedores": fornecedores})
