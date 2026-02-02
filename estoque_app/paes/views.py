"""
Views do módulo PÃES.
Dashboard: visão rápida (cards, gráficos, entregas, produção, alertas).
Clientes: CRUD (listagem, novo, editar, inativar).
Planos e Entregas.
"""
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST

from estoque_app.paes.cliente_pao_service import (
    listar_clientes_ativos,
    obter_por_id,
    criar,
    atualizar,
    inativar,
)
from estoque_app.paes.plano_entrega_pao_service import (
    listar_agrupado_por_tipo,
    obter_por_id as obter_plano_por_id,
    criar as criar_plano,
    atualizar as atualizar_plano,
    cancelar as cancelar_plano,
    DIAS_SEMANA,
    TIPO_PLANO_CHOICES,
)


def dashboard(request):
    """HOME do módulo PÃES: cards, gráficos, entregas hoje/amanhã, produção, alertas financeiros."""
    from estoque_app.paes.paes_dashboard_service import get_dashboard_context
    try:
        ctx = get_dashboard_context()
    except Exception as e:
        from django.contrib import messages
        messages.error(request, str(e))
        ctx = {
            "cards": {"operacional": {}, "financeiro": {}},
            "grafico_paes": [],
            "grafico_recebimentos": {},
            "entregas_hoje": [],
            "entregas_amanha": [],
            "producao_amanha": {"itens": [], "total_paes": 0, "total_entregas": 0},
            "em_atraso": [],
            "a_receber_semana": [],
            "hoje_fmt": "",
            "amanha_fmt": "",
            "amanha_iso": "",
        }
    return render(request, "estoque_app/paes/dashboard.html", {
        "page_title": "Pães — Dashboard",
        **ctx,
    })


def ordem_producao_pdf(request):
    """
    Gera Ordem de Produção em PDF para um dia.
    GET ?data=YYYY-MM-DD — se omitido, usa amanhã.
    Reutiliza resumo_producao_por_data e listar_entregas_por_data. Não altera banco.
    """
    from datetime import date, timedelta
    from estoque_app.paes.entrega_pao_service import (
        gerar_entregas_para_periodo,
        resumo_producao_por_data,
        listar_entregas_por_data,
    )
    from estoque_app.paes.ordem_producao_pdf_service import gerar_ordem_producao_pdf

    data_str = request.GET.get("data", "").strip()
    if data_str:
        try:
            data_producao = date.fromisoformat(data_str[:10])
        except (ValueError, TypeError):
            data_producao = date.today() + timedelta(days=1)
    else:
        data_producao = date.today() + timedelta(days=1)

    try:
        gerar_entregas_para_periodo(data_producao, data_producao)
        resumo = resumo_producao_por_data(data_producao)
        entregas = listar_entregas_por_data(data_producao)
    except Exception as e:
        return HttpResponse(f"Erro ao gerar dados: {e}", status=500)

    pdf_buffer = gerar_ordem_producao_pdf(data_producao, resumo, entregas)
    response = HttpResponse(pdf_buffer.read(), content_type="application/pdf")
    filename = f"ordem_producao_{data_producao.isoformat()}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def clientes_list(request):
    """Lista apenas clientes ativos, ordenados por nome."""
    try:
        clientes = listar_clientes_ativos()
    except Exception as e:
        messages.error(request, f"Erro ao listar clientes: {e}")
        clientes = []
    return render(request, "estoque_app/paes/clientes/list.html", {
        "page_title": "Pães — Clientes",
        "clientes": clientes,
    })


def clientes_novo(request):
    """GET: exibe formulário. POST: salva cliente e redireciona para listagem."""
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        telefone = request.POST.get("telefone", "").strip()
        endereco = request.POST.get("endereco", "").strip()
        observacoes = request.POST.get("observacoes", "").strip()
        try:
            criar(nome=nome, telefone=telefone, endereco=endereco, observacoes=observacoes)
            messages.success(request, "Cliente cadastrado com sucesso.")
            return redirect("estoque_app:paes_clientes_list")
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "estoque_app/paes/clientes/form.html", {
                "page_title": "Pães — Novo cliente",
                "form_data": request.POST,
            })
        except Exception as e:
            messages.error(request, f"Erro ao salvar: {e}")
            return render(request, "estoque_app/paes/clientes/form.html", {
                "page_title": "Pães — Novo cliente",
                "form_data": request.POST,
            })
    return render(request, "estoque_app/paes/clientes/form.html", {
        "page_title": "Pães — Novo cliente",
    })


def clientes_editar(request, cliente_id):
    """Edita cliente existente. Mantém created_at, atualiza updated_at."""
    cliente = obter_por_id(cliente_id)
    if not cliente:
        messages.error(request, "Cliente não encontrado.")
        return redirect("estoque_app:paes_clientes_list")
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        telefone = request.POST.get("telefone", "").strip()
        endereco = request.POST.get("endereco", "").strip()
        observacoes = request.POST.get("observacoes", "").strip()
        try:
            atualizar(
                cliente_id=cliente_id,
                nome=nome,
                telefone=telefone,
                endereco=endereco,
                observacoes=observacoes,
                created_at=cliente.get("created_at"),
            )
            messages.success(request, "Cliente atualizado com sucesso.")
            return redirect("estoque_app:paes_clientes_list")
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "estoque_app/paes/clientes/form.html", {
                "page_title": "Pães — Editar cliente",
                "cliente": cliente,
                "form_data": request.POST,
            })
        except Exception as e:
            messages.error(request, f"Erro ao atualizar: {e}")
            return render(request, "estoque_app/paes/clientes/form.html", {
                "page_title": "Pães — Editar cliente",
                "cliente": cliente,
                "form_data": request.POST,
            })
    return render(request, "estoque_app/paes/clientes/form.html", {
        "page_title": "Pães — Editar cliente",
        "cliente": cliente,
    })


@require_POST
def clientes_inativar(request, cliente_id):
    """Soft delete: ativo = False. Redireciona para listagem."""
    if inativar(cliente_id):
        messages.success(request, "Cliente inativado com sucesso.")
    else:
        messages.error(request, "Cliente não encontrado ou já inativo.")
    return redirect("estoque_app:paes_clientes_list")


def planos_list(request):
    """Lista planos agrupados por tipo (Diário, Semanal, Mensal) e por status (Ativos, Em atraso, Cancelados)."""
    try:
        agrupado = listar_agrupado_por_tipo()
    except Exception as e:
        messages.error(request, f"Erro ao listar planos: {e}")
        agrupado = {"DIARIO": {"ativos": [], "em_atraso": [], "cancelados": []}, "SEMANAL": {"ativos": [], "em_atraso": [], "cancelados": []}, "MENSAL": {"ativos": [], "em_atraso": [], "cancelados": []}}
    secoes = [
        ("DIARIO", "Diário", agrupado.get("DIARIO", {"ativos": [], "em_atraso": [], "cancelados": []})),
        ("SEMANAL", "Semanal", agrupado.get("SEMANAL", {"ativos": [], "em_atraso": [], "cancelados": []})),
        ("MENSAL", "Mensal", agrupado.get("MENSAL", {"ativos": [], "em_atraso": [], "cancelados": []})),
    ]
    return render(request, "estoque_app/paes/planos/list.html", {
        "page_title": "Pães — Planos de entrega",
        "secoes": secoes,
    })


def planos_novo(request):
    """GET: exibe formulário. POST: cria plano (status ATIVO, status_pagamento PENDENTE, calcula valor_total)."""
    clientes = listar_clientes_ativos()
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id", "").strip()
        tipo_plano = request.POST.get("tipo_plano", "SEMANAL").strip().upper()
        dias_entrega = request.POST.getlist("dias_entrega")
        horario_entrega = request.POST.get("horario_entrega", "06:00").strip()[:5]
        quantidade_paes_por_dia = request.POST.get("quantidade_paes_por_dia", "0").strip()
        valor_por_pao = request.POST.get("valor_por_pao", "0").strip().replace(",", ".")
        data_pagamento = request.POST.get("data_pagamento", "").strip()
        try:
            qtd = int(quantidade_paes_por_dia)
            valor = float(valor_por_pao) if valor_por_pao else 0.0
        except (ValueError, TypeError):
            qtd = 0
            valor = 0.0
        try:
            criar_plano(
                cliente_id=cliente_id,
                tipo_plano=tipo_plano,
                dias_entrega=dias_entrega,
                horario_entrega=horario_entrega,
                quantidade_paes_por_dia=qtd,
                valor_por_pao=valor,
                data_pagamento=data_pagamento or None,
            )
            messages.success(request, "Plano criado com sucesso.")
            return redirect("estoque_app:paes_planos_list")
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "estoque_app/paes/planos/form.html", {
                "page_title": "Pães — Novo plano",
                "clientes": clientes,
                "dias_semana": DIAS_SEMANA,
                "tipo_plano_choices": TIPO_PLANO_CHOICES,
                "form_data": request.POST,
                "form_dias": request.POST.getlist("dias_entrega"),
            })
        except Exception as e:
            messages.error(request, f"Erro ao salvar: {e}")
            return render(request, "estoque_app/paes/planos/form.html", {
                "page_title": "Pães — Novo plano",
                "clientes": clientes,
                "dias_semana": DIAS_SEMANA,
                "tipo_plano_choices": TIPO_PLANO_CHOICES,
                "form_data": request.POST,
                "form_dias": request.POST.getlist("dias_entrega"),
            })
    return render(request, "estoque_app/paes/planos/form.html", {
        "page_title": "Pães — Novo plano",
        "clientes": clientes,
        "dias_semana": DIAS_SEMANA,
        "tipo_plano_choices": TIPO_PLANO_CHOICES,
    })


def planos_editar(request, plano_id):
    """Edita dias, quantidade, valor_por_pao, data_pagamento. Recalcula valor_total."""
    plano = obter_plano_por_id(plano_id)
    if not plano:
        messages.error(request, "Plano não encontrado.")
        return redirect("estoque_app:paes_planos_list")
    if plano.get("status") == "CANCELADO":
        messages.error(request, "Não é possível editar plano cancelado.")
        return redirect("estoque_app:paes_planos_list")
    if request.method == "POST":
        dias_entrega = request.POST.getlist("dias_entrega")
        quantidade_paes_por_dia = request.POST.get("quantidade_paes_por_dia", "0").strip()
        valor_por_pao = request.POST.get("valor_por_pao", "0").strip().replace(",", ".")
        data_pagamento = request.POST.get("data_pagamento", "").strip()
        try:
            qtd = int(quantidade_paes_por_dia)
            valor = float(valor_por_pao) if valor_por_pao else 0.0
        except (ValueError, TypeError):
            qtd = 0
            valor = 0.0
        try:
            atualizar_plano(
                plano_id=plano_id,
                dias_entrega=dias_entrega,
                quantidade_paes_por_dia=qtd,
                valor_por_pao=valor,
                data_pagamento=data_pagamento or None,
            )
            messages.success(request, "Plano atualizado com sucesso.")
            return redirect("estoque_app:paes_planos_list")
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "estoque_app/paes/planos/form.html", {
                "page_title": "Pães — Editar plano",
                "plano": plano,
                "clientes": listar_clientes_ativos(),
                "dias_semana": DIAS_SEMANA,
                "tipo_plano_choices": TIPO_PLANO_CHOICES,
                "form_data": request.POST,
                "form_dias": request.POST.getlist("dias_entrega"),
            })
        except Exception as e:
            messages.error(request, f"Erro ao atualizar: {e}")
            return render(request, "estoque_app/paes/planos/form.html", {
                "page_title": "Pães — Editar plano",
                "plano": plano,
                "clientes": listar_clientes_ativos(),
                "dias_semana": DIAS_SEMANA,
                "tipo_plano_choices": TIPO_PLANO_CHOICES,
                "form_data": request.POST,
                "form_dias": request.POST.getlist("dias_entrega"),
            })
    return render(request, "estoque_app/paes/planos/form.html", {
        "page_title": "Pães — Editar plano",
        "plano": plano,
        "clientes": listar_clientes_ativos(),
        "dias_semana": DIAS_SEMANA,
        "tipo_plano_choices": TIPO_PLANO_CHOICES,
    })


@require_POST
def planos_cancelar(request, plano_id):
    """Soft cancel: status = CANCELADO. Redireciona para listagem."""
    if cancelar_plano(plano_id):
        messages.success(request, "Plano cancelado com sucesso.")
    else:
        messages.error(request, "Plano não encontrado.")
    return redirect("estoque_app:paes_planos_list")


def entregas_list(request):
    """
    Agenda de entregas. Antes de exibir: gerar_entregas_para_periodo(hoje, hoje+7).
    Exibe: Bloco 1 Entregas HOJE, Bloco 2 AMANHÃ, Bloco 3 Próximos dias, Bloco EXTRA Produção de amanhã.
    """
    from datetime import date, timedelta
    from estoque_app.paes.entrega_pao_service import (
        gerar_entregas_para_periodo,
        listar_entregas_por_data,
        listar_entregas_agrupadas_por_data,
        resumo_producao_por_data,
    )
    hoje = date.today()
    amanha = hoje + timedelta(days=1)
    fim_periodo = hoje + timedelta(days=7)
    try:
        gerar_entregas_para_periodo(hoje, fim_periodo)
    except Exception as e:
        messages.error(request, f"Erro ao atualizar agenda: {e}")
    try:
        entregas_hoje = listar_entregas_por_data(hoje)
        entregas_amanha = listar_entregas_por_data(amanha)
        # Próximos dias: do dia depois de amanhã até +7
        inicio_proximos = amanha + timedelta(days=1)
        proximos_agrupado = listar_entregas_agrupadas_por_data(inicio_proximos, fim_periodo)
        # Ordenar chaves e incluir total de pães por dia (lista de dicts para o template)
        proximos_dias = []
        for k in sorted(proximos_agrupado.keys()):
            lista = proximos_agrupado[k]
            total_paes = sum(e.get("quantidade_paes") or 0 for e in lista)
            proximos_dias.append({"data_key": k, "lista": lista, "total_paes": total_paes})
        producao_amanha = resumo_producao_por_data(amanha)
    except Exception as e:
        messages.error(request, f"Erro ao carregar entregas: {e}")
        entregas_hoje = []
        entregas_amanha = []
        proximos_dias = []  # lista de (data_key, lista_entregas, total_paes)
        producao_amanha = {"itens": [], "total_paes": 0, "total_entregas": 0}
    return render(request, "estoque_app/paes/entregas/list.html", {
        "page_title": "Pães — Agenda de entregas",
        "entregas_hoje": entregas_hoje,
        "entregas_amanha": entregas_amanha,
        "proximos_dias": proximos_dias,
        "producao_amanha": producao_amanha,
        "hoje_fmt": hoje.strftime("%d/%m/%Y"),
        "amanha_fmt": amanha.strftime("%d/%m/%Y"),
    })


@require_POST
def entrega_confirmar(request, entrega_id):
    """Marca entrega como ENTREGUE e define data_confirmacao. Redireciona para agenda."""
    from estoque_app.paes.entrega_pao_service import confirmar_entrega
    if confirmar_entrega(entrega_id):
        messages.success(request, "Entrega confirmada.")
    else:
        messages.error(request, "Entrega não encontrada ou já confirmada.")
    return redirect("estoque_app:paes_entregas_list")


# ---------- Financeiro (títulos a receber) ----------

def financeiro_pendentes(request):
    """
    Títulos a receber pendentes. Antes: gerar_titulos_para_periodo(hoje, hoje+30).
    Exibe: Esta semana, Semana que vem, Em atraso (destaque vermelho, dias atrasado).
    """
    from datetime import date, timedelta
    from estoque_app.paes.titulo_receber_pao_service import (
        gerar_titulos_para_periodo,
        listar_pendentes_agrupados,
    )
    hoje = date.today()
    fim_periodo = hoje + timedelta(days=30)
    try:
        gerar_titulos_para_periodo(hoje, fim_periodo)
    except Exception as e:
        messages.error(request, f"Erro ao atualizar títulos: {e}")
    try:
        agrupado = listar_pendentes_agrupados()
    except Exception as e:
        messages.error(request, f"Erro ao carregar títulos: {e}")
        agrupado = {"esta_semana": [], "semana_que_vem": [], "em_atraso": []}
    return render(request, "estoque_app/paes/financeiro/pendentes.html", {
        "page_title": "Pães — Títulos a receber",
        "esta_semana": agrupado["esta_semana"],
        "semana_que_vem": agrupado["semana_que_vem"],
        "em_atraso": agrupado["em_atraso"],
    })


def financeiro_registrar(request, titulo_id):
    """GET: formulário (forma de pagamento, data, observações). POST: marca status=PAGO e redireciona."""
    from estoque_app.paes.titulo_receber_pao_service import obter_por_id, registrar_pagamento, FORMAS_PAGAMENTO
    titulo = obter_por_id(titulo_id)
    if not titulo:
        messages.error(request, "Título não encontrado.")
        return redirect("estoque_app:paes_financeiro_pendentes")
    if titulo.get("status") == "PAGO":
        messages.warning(request, "Este título já foi pago.")
        return redirect("estoque_app:paes_financeiro_pendentes")
    if request.method == "POST":
        data_pagamento = request.POST.get("data_pagamento", "").strip()
        forma_pagamento = request.POST.get("forma_pagamento", "").strip()
        observacoes = request.POST.get("observacoes", "").strip()
        if not data_pagamento:
            messages.error(request, "Data do pagamento é obrigatória.")
            return render(request, "estoque_app/paes/financeiro/registrar.html", {
                "page_title": "Pães — Registrar pagamento",
                "titulo": titulo,
                "formas_pagamento": FORMAS_PAGAMENTO,
                "form_data": request.POST,
            })
        if registrar_pagamento(titulo_id, data_pagamento=data_pagamento, forma_pagamento=forma_pagamento, observacoes=observacoes):
            messages.success(request, "Pagamento registrado com sucesso.")
            return redirect("estoque_app:paes_financeiro_pendentes")
        messages.error(request, "Erro ao registrar pagamento.")
    return render(request, "estoque_app/paes/financeiro/registrar.html", {
        "page_title": "Pães — Registrar pagamento",
        "titulo": titulo,
        "formas_pagamento": FORMAS_PAGAMENTO,
    })


def financeiro_pagos(request):
    """Listagem de títulos pagos. Filtro por período (GET). Total recebido no período."""
    from datetime import date, timedelta
    from estoque_app.paes.titulo_receber_pao_service import listar_pagos
    hoje = date.today()
    # Período padrão: mês atual
    inicio_mes = hoje.replace(day=1)
    if hoje.month == 12:
        fim_mes = hoje.replace(day=31)
    else:
        fim_mes = date(hoje.year, hoje.month + 1, 1) - timedelta(days=1)
    periodo_inicio_str = request.GET.get("data_inicio", inicio_mes.isoformat())
    periodo_fim_str = request.GET.get("data_fim", fim_mes.isoformat())
    try:
        periodo_inicio = date.fromisoformat(periodo_inicio_str)
        periodo_fim = date.fromisoformat(periodo_fim_str)
    except (ValueError, TypeError):
        periodo_inicio = inicio_mes
        periodo_fim = fim_mes
    if periodo_inicio > periodo_fim:
        periodo_inicio, periodo_fim = periodo_fim, periodo_inicio
    try:
        titulos_pagos_lista, total_recebido = listar_pagos(periodo_inicio, periodo_fim)
    except Exception as e:
        messages.error(request, f"Erro ao carregar: {e}")
        titulos_pagos_lista = []
        total_recebido = 0.0
    return render(request, "estoque_app/paes/financeiro/pagos.html", {
        "page_title": "Pães — Títulos pagos",
        "titulos": titulos_pagos_lista,
        "total_recebido": total_recebido,
        "periodo_inicio": periodo_inicio.isoformat(),
        "periodo_fim": periodo_fim.isoformat(),
    })
