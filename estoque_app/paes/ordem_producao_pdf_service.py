"""
Geração do PDF único: Ordem de Produção (pág. 1) + Comprovante de Entrega (pág. 2).
Usa reportlab. Não altera banco; informativo para padeiro e comprovante para entregador.
"""
from io import BytesIO
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from typing import Dict, Any, List


def gerar_ordem_producao_pdf(
    data_producao: date,
    resumo: Dict[str, Any],
    entregas: List[Dict[str, Any]],
) -> BytesIO:
    """
    Gera PDF de duas páginas:
    Página 1 — Ordem de Produção (resumo para o padeiro).
    Página 2 — Comprovante de Entrega (tabela com colunas em branco para assinatura).
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin_left = 20 * mm
    margin_right = width - 20 * mm
    margin_top = height - 25 * mm
    line_height = 5.5 * mm
    data_prod_fmt = data_producao.strftime("%d/%m/%Y")

    # ========== PÁGINA 1 — ORDEM DE PRODUÇÃO ==========
    current_y = margin_top

    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2, current_y, "Ordem de Produção – Pães")
    current_y -= line_height * 1.2

    p.setFont("Helvetica", 10)
    p.drawString(margin_left, current_y, f"Data da produção: {data_prod_fmt}")
    current_y -= line_height
    p.drawString(margin_left, current_y, f"Data de geração do documento: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    current_y -= line_height * 1.5
    p.line(margin_left, current_y, margin_right, current_y)
    current_y -= line_height

    # Resumo da Produção
    p.setFont("Helvetica-Bold", 12)
    p.drawString(margin_left, current_y, f"Produção do dia {data_prod_fmt}")
    current_y -= line_height * 1.2

    itens = resumo.get("itens") or []
    total_paes = resumo.get("total_paes") or 0

    p.setFont("Helvetica", 10)
    for (qtd_paes, num_sacos) in itens:
        texto = f"• {num_sacos} saco(s) com {qtd_paes} pães"
        p.drawString(margin_left, current_y, texto)
        current_y -= line_height

    current_y -= line_height * 0.5
    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin_left, current_y, f"Total de pães: {total_paes}")
    current_y -= line_height * 2
    p.line(margin_left, current_y, margin_right, current_y)
    current_y -= line_height
    p.setFont("Helvetica", 9)
    p.drawCentredString(width / 2, current_y, "Documento gerado automaticamente pelo sistema.")

    # ========== PÁGINA 2 — COMPROVANTE DE ENTREGA ==========
    p.showPage()
    current_y = margin_top

    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2, current_y, "Comprovante de Entrega – Pães")
    current_y -= line_height * 1.5

    # Tabela: Cliente | Endereço | Qtd. pães | Nome de quem recebeu | Assinatura
    # Larguras (mm): 38 | 52 | 18 | 32 | 30 — margens laterais iguais ao título
    w_cli, w_end, w_qtd, w_nome, w_assi = 38 * mm, 52 * mm, 18 * mm, 32 * mm, 30 * mm
    x_cliente = margin_left
    x_endereco = x_cliente + w_cli
    x_qtd = x_endereco + w_end
    x_nome = x_qtd + w_qtd
    x_assinatura = x_nome + w_nome
    # Centros das colunas centralizadas (Qtd., Nome, Assinatura)
    cx_qtd = x_qtd + w_qtd / 2
    cx_nome = x_nome + w_nome / 2
    cx_assi = x_assinatura + w_assi / 2
    row_height = 14 * mm  # altura maior para assinatura manual
    header_sep = line_height * 0.6

    # Cabeçalho da tabela — negrito, alinhado com as colunas, separador abaixo
    p.setFont("Helvetica-Bold", 9)
    p.drawString(x_cliente, current_y, "Cliente")
    p.drawString(x_endereco, current_y, "Endereço")
    p.drawCentredString(cx_qtd, current_y, "Qtd. pães")
    p.drawCentredString(cx_nome, current_y, "Nome")
    p.drawCentredString(cx_assi, current_y, "Assinatura")
    current_y -= header_sep
    p.line(margin_left, current_y, margin_right, current_y)
    current_y -= line_height * 0.4

    # Linhas de dados — Cliente e Endereço à esquerda; Qtd. centralizado; Nome e Assinatura em branco
    p.setFont("Helvetica", 9)
    for e in entregas:
        nome = (e.get("nome_cliente") or "—")[:24]
        endereco = (e.get("endereco_cliente") or "—")[:38]
        qtd = e.get("quantidade_paes") or 0
        p.drawString(x_cliente, current_y, nome)
        p.drawString(x_endereco, current_y, endereco)
        p.drawCentredString(cx_qtd, current_y, str(qtd))
        # Nome de quem recebeu e Assinatura: em branco (centralizado visualmente)
        current_y -= row_height
        p.line(margin_left, current_y, margin_right, current_y)
        current_y -= line_height * 0.25

    # Texto declaratório — alinhado à esquerda, mesma margem, espaçamento confortável
    current_y -= line_height * 1.2
    p.setFont("Helvetica", 10)
    p.drawString(margin_left, current_y, "Declaro que recebi os produtos descritos acima na data informada.")
    current_y -= line_height * 2.2

    # Rodapé — Assinatura do entregador e Data centralizados e bem espaçados
    p.setFont("Helvetica", 8)
    p.drawCentredString(width / 2, current_y, "Assinatura do entregador")
    current_y -= line_height * 1.2
    p.line(margin_left + 45 * mm, current_y, margin_right - 45 * mm, current_y)
    current_y -= line_height * 1.8
    p.drawCentredString(width / 2, current_y, "Data")
    current_y -= line_height * 0.8
    p.line(margin_left + 75 * mm, current_y, margin_right - 75 * mm, current_y)

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
