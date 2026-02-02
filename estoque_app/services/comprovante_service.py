"""
Service para geração de comprovantes em PDF.

Localização: estoque_app/services/comprovante_service.py

Este service gera comprovantes de venda em PDF usando reportlab.
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from typing import Dict, Any


def gerar_comprovante_pdf(venda: Dict[str, Any]) -> BytesIO:
    """
    Gera um comprovante de venda em PDF.
    
    Args:
        venda: Dict com dados da venda (deve conter itens, valor_total_venda, created_at)
    
    Returns:
        BytesIO com o conteúdo do PDF
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Margens
    margin_left = 20 * mm
    margin_top = height - 30 * mm
    line_height = 6 * mm
    current_y = margin_top
    
    # Título
    p.setFont("Helvetica-Bold", 18)
    p.drawString(margin_left, current_y, "COMPROVANTE DE VENDA")
    current_y -= line_height * 1.5
    
    # Data e hora
    p.setFont("Helvetica", 10)
    data_venda = venda.get('created_at')
    if isinstance(data_venda, datetime):
        data_str = data_venda.strftime("%d/%m/%Y %H:%M:%S")
    elif isinstance(data_venda, str):
        # Tenta converter string ISO para datetime
        try:
            # Formato ISO: 2024-01-15T10:30:00 ou 2024-01-15T10:30:00.000Z
            if 'T' in data_venda:
                dt_str = data_venda.split('T')[0] + ' ' + data_venda.split('T')[1].split('.')[0].split('Z')[0]
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                data_str = dt.strftime("%d/%m/%Y %H:%M:%S")
            else:
                data_str = data_venda
        except:
            data_str = data_venda
    else:
        data_str = "Data não disponível"
    
    p.drawString(margin_left, current_y, f"Data: {data_str}")
    current_y -= line_height * 1.5
    
    # Linha separadora
    p.line(margin_left, current_y, width - margin_left, current_y)
    current_y -= line_height
    
    # Cabeçalho da tabela
    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin_left, current_y, "PRODUTO")
    p.drawString(margin_left + 80 * mm, current_y, "QTD")
    p.drawString(margin_left + 100 * mm, current_y, "UNITÁRIO")
    p.drawString(margin_left + 140 * mm, current_y, "TOTAL")
    current_y -= line_height
    
    # Linha separadora
    p.line(margin_left, current_y, width - margin_left, current_y)
    current_y -= line_height * 0.5
    
    # Itens da venda
    p.setFont("Helvetica", 9)
    itens = venda.get('itens', [])
    
    for item in itens:
        nome = item.get('nome', '')[:40]  # Limita tamanho do nome
        quantidade = item.get('quantidade', 0)
        valor_unitario = item.get('valor_unitario', 0)
        valor_total = item.get('valor_total', 0)
        
        # Nome do produto (pode quebrar linha se necessário)
        p.drawString(margin_left, current_y, nome)
        
        # Quantidade
        p.drawString(margin_left + 80 * mm, current_y, str(quantidade))
        
        # Valor unitário
        p.drawString(margin_left + 100 * mm, current_y, f"R$ {valor_unitario:.2f}")
        
        # Valor total
        p.drawString(margin_left + 140 * mm, current_y, f"R$ {valor_total:.2f}")
        
        current_y -= line_height
        
        # Quebra de página se necessário
        if current_y < 50 * mm:
            p.showPage()
            current_y = height - 30 * mm
    
    # Linha separadora antes do total
    current_y -= line_height * 0.5
    p.line(margin_left, current_y, width - margin_left, current_y)
    current_y -= line_height
    
    # Valor total da venda
    p.setFont("Helvetica-Bold", 12)
    valor_total_venda = venda.get('valor_total_venda', 0)
    p.drawString(margin_left + 100 * mm, current_y, "TOTAL:")
    p.drawString(margin_left + 140 * mm, current_y, f"R$ {valor_total_venda:.2f}")
    
    # Rodapé
    current_y -= line_height * 2
    p.setFont("Helvetica", 8)
    p.drawString(margin_left, current_y, "Obrigado pela sua compra!")
    
    # Finaliza o PDF
    p.showPage()
    p.save()
    
    # Retorna o buffer
    buffer.seek(0)
    return buffer


def gerar_comprovante_emporium_pdf(venda: Dict[str, Any]) -> BytesIO:
    """
    Gera comprovante em PDF para vendas Emporium Prime (processados ou atacado).
    Layout: Emporium Prime, número, data, tipo; tabela Produto / Peso ou Qtd / Unitário / Subtotal; total.
    Não exibe custo, lucro ou divisão de lucro.

    Args:
        venda: Dict normalizado com numero_venda, data_venda, tipo_venda_label, itens, valor_total_venda.
              itens: lista de { nome, quantidade, valor_unitario, valor_total }

    Returns:
        BytesIO com o conteúdo do PDF
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_left = 20 * mm
    margin_top = height - 30 * mm
    line_height = 6 * mm
    current_y = margin_top

    # Cabeçalho — Nome do negócio
    p.setFont("Helvetica-Bold", 18)
    p.drawString(margin_left, current_y, "Emporium Prime")
    current_y -= line_height * 1.2

    p.setFont("Helvetica", 10)
    numero = venda.get("numero_venda", "")
    p.drawString(margin_left, current_y, f"Número da venda: {numero}")
    current_y -= line_height

    data_venda = venda.get("data_venda")
    if isinstance(data_venda, datetime):
        data_str = data_venda.strftime("%d/%m/%Y")
    elif hasattr(data_venda, "strftime"):
        data_str = data_venda.strftime("%d/%m/%Y")
    elif isinstance(data_venda, str):
        data_str = data_venda[:10] if len(data_venda) >= 10 else data_venda
    else:
        data_str = "—"
    p.drawString(margin_left, current_y, f"Data da venda: {data_str}")
    current_y -= line_height

    tipo_label = venda.get("tipo_venda_label", "Venda")
    p.drawString(margin_left, current_y, f"Tipo da venda: {tipo_label}")
    current_y -= line_height * 1.5

    p.line(margin_left, current_y, width - margin_left, current_y)
    current_y -= line_height

    # Cabeçalho da tabela
    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin_left, current_y, "PRODUTO")
    p.drawString(margin_left + 75 * mm, current_y, "QTD/PESO")
    p.drawString(margin_left + 105 * mm, current_y, "UNITÁRIO")
    p.drawString(margin_left + 140 * mm, current_y, "SUBTOTAL")
    current_y -= line_height
    p.line(margin_left, current_y, width - margin_left, current_y)
    current_y -= line_height * 0.5

    # Itens
    p.setFont("Helvetica", 9)
    itens = venda.get("itens", [])
    for item in itens:
        nome = (item.get("nome") or "")[:45]
        quantidade = item.get("quantidade", "")
        valor_unitario = float(item.get("valor_unitario", 0))
        valor_total = float(item.get("valor_total", 0))
        p.drawString(margin_left, current_y, nome)
        p.drawString(margin_left + 75 * mm, current_y, str(quantidade))
        p.drawString(margin_left + 105 * mm, current_y, f"R$ {valor_unitario:.2f}")
        p.drawString(margin_left + 140 * mm, current_y, f"R$ {valor_total:.2f}")
        current_y -= line_height
        if current_y < 50 * mm:
            p.showPage()
            current_y = height - 30 * mm
            p.setFont("Helvetica", 9)

    current_y -= line_height * 0.5
    p.line(margin_left, current_y, width - margin_left, current_y)
    current_y -= line_height

    # Valor total
    p.setFont("Helvetica-Bold", 12)
    valor_total_venda = float(venda.get("valor_total_venda", 0))
    p.drawString(margin_left + 105 * mm, current_y, "TOTAL:")
    p.drawString(margin_left + 140 * mm, current_y, f"R$ {valor_total_venda:.2f}")

    current_y -= line_height * 2
    p.setFont("Helvetica", 8)
    p.drawString(margin_left, current_y, "Obrigado pela sua compra!")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


def gerar_tabela_precos_pdf(itens: list) -> BytesIO:
    """
    Gera PDF da tabela de preços (produtos comerciais ativos Emporium Prime).
    itens: lista de dict com nome_comercial, tipo, preco_venda_kg.
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin_left = 20 * mm
    margin_top = height - 30 * mm
    line_height = 6 * mm
    current_y = margin_top

    p.setFont("Helvetica-Bold", 18)
    p.drawString(margin_left, current_y, "Emporium Prime — Tabela de Preços")
    current_y -= line_height * 1.5
    p.setFont("Helvetica", 10)
    p.drawString(margin_left, current_y, f"Gerado em: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}")
    current_y -= line_height * 1.5
    p.line(margin_left, current_y, width - margin_left, current_y)
    current_y -= line_height

    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin_left, current_y, "Produto")
    p.drawString(margin_left + 90 * mm, current_y, "Tipo")
    p.drawString(margin_left + 120 * mm, current_y, "Preço/kg (R$)")
    current_y -= line_height
    p.line(margin_left, current_y, width - margin_left, current_y)
    current_y -= line_height * 0.5

    p.setFont("Helvetica", 9)
    for item in itens:
        nome = (item.get("nome_comercial") or "")[:45]
        tipo = item.get("tipo", "")
        preco = float(item.get("preco_venda_kg", 0))
        p.drawString(margin_left, current_y, nome)
        p.drawString(margin_left + 90 * mm, current_y, tipo)
        p.drawString(margin_left + 120 * mm, current_y, f"R$ {preco:.2f}")
        current_y -= line_height
        if current_y < 50 * mm:
            p.showPage()
            current_y = height - 30 * mm
            p.setFont("Helvetica", 9)

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
