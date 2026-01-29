"""
Views de despesas operacionais.

Views simples que chamam o service e renderizam templates.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from estoque_app.services import despesa_service


def despesa_list(request):
    """
    Lista todas as despesas.
    GET → exibe tabela ordenada da mais recente para a mais antiga.
    Rota: /despesas/
    """
    try:
        despesas = despesa_service.listar_despesas()
        return render(request, "estoque_app/despesas/list.html", {"despesas": despesas})
    except Exception as e:
        messages.error(request, f"Erro ao listar despesas: {str(e)}")
        return render(request, "estoque_app/despesas/list.html", {"despesas": []})


def despesa_create(request):
    """
    Cadastro de nova despesa.
    GET → exibe formulário.
    POST → valida, cria despesa e redireciona para listagem com mensagem de sucesso.
    Rota: /despesas/nova/
    """
    if request.method == "POST":
        descricao = request.POST.get("descricao", "").strip()
        categoria = request.POST.get("categoria", "").strip()
        valor = request.POST.get("valor", "").strip()
        data = request.POST.get("data", "").strip()

        if not descricao:
            messages.error(request, "Descrição é obrigatória.")
            return render(
                request,
                "estoque_app/despesas/form.html",
                {"form_data": request.POST, "page_title": "Nova Despesa - Estoque"},
            )
        if not data:
            messages.error(request, "Data é obrigatória.")
            return render(
                request,
                "estoque_app/despesas/form.html",
                {"form_data": request.POST, "page_title": "Nova Despesa - Estoque"},
            )
        try:
            valor_f = float(valor.replace(",", ".")) if valor else 0
        except ValueError:
            messages.error(request, "Valor inválido.")
            return render(
                request,
                "estoque_app/despesas/form.html",
                {"form_data": request.POST, "page_title": "Nova Despesa - Estoque"},
            )
        if valor_f <= 0:
            messages.error(request, "Valor deve ser maior que zero.")
            return render(
                request,
                "estoque_app/despesas/form.html",
                {"form_data": request.POST, "page_title": "Nova Despesa - Estoque"},
            )

        try:
            despesa_service.criar_despesa({
                "descricao": descricao,
                "categoria": categoria,
                "valor": valor_f,
                "data": data,
            })
            messages.success(request, "Despesa cadastrada com sucesso.")
            return redirect("estoque_app:despesa_list")
        except ValueError as e:
            messages.error(request, str(e))
            return render(
                request,
                "estoque_app/despesas/form.html",
                {"form_data": request.POST, "page_title": "Nova Despesa - Estoque"},
            )
        except Exception as e:
            messages.error(request, f"Erro ao salvar despesa: {str(e)}")
            return render(
                request,
                "estoque_app/despesas/form.html",
                {"form_data": request.POST, "page_title": "Nova Despesa - Estoque"},
            )

    return render(
        request,
        "estoque_app/despesas/form.html",
        {"page_title": "Nova Despesa - Estoque"},
    )
