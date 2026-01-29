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
