import io
from datetime import datetime
from decimal import Decimal
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.models.models import (
    Orden, EstadoOrden, TransaccionPago, Usuario,
    Producto, DetalleOrden, RecetaEscandallo
)

def generar_excel_auditoria_ventas(db: Session) -> io.BytesIO:
    """
    Genera el libro Excel de auditoría y proyecciones en memoria usando openpyxl.
    Estilos Apple Tinted Dark: Fondo oscuro #141416, dorado #D4AF37 y textos limpios.
    """
    wb = openpyxl.Workbook()
    # Eliminar hoja por defecto
    wb.remove(wb.active)

    # Estilos comunes de marca Bourlemont
    header_fill = PatternFill(start_color="141416", end_color="141416", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="D4AF37")
    title_font = Font(name="Segoe UI", size=14, bold=True, color="141416")
    sub_font = Font(name="Segoe UI", size=10, italic=True, color="555555")
    cell_font = Font(name="Segoe UI", size=10, color="000000")
    bold_cell_font = Font(name="Segoe UI", size=10, bold=True, color="000000")
    
    thin_gold = Side(border_style="thin", color="D4AF37")
    thin_gray = Side(border_style="thin", color="E0E0E0")
    cell_border = Border(top=thin_gray, left=thin_gray, right=thin_gray, bottom=thin_gray)
    header_border = Border(top=thin_gold, left=thin_gold, right=thin_gold, bottom=thin_gold)

    # ==============================================================
    # HOJA 1: Ventas Detalladas
    # ==============================================================
    ws1 = wb.create_sheet(title="Ventas Detalladas")
    ws1.views.sheetView[0].showGridLines = True
    
    # Encabezado de Marca
    ws1["A1"] = "BOURLEMONT CHAMPAGNE BAR"
    ws1["A1"].font = title_font
    ws1["A2"] = f"Reporte de Auditoría de Ventas Detalladas - Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws1["A2"].font = sub_font
    
    headers1 = [
        "ID Orden", "Fecha / Hora", "Mesa / Ubicación", "Bartender",
        "Detalle de Productos", "Método de Pago", "Total Facturado (Q)"
    ]
    
    row_idx = 4
    for col_idx, h in enumerate(headers1, start=1):
        cell = ws1.cell(row=row_idx, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = header_border
        
    ordenes = db.query(Orden).filter(Orden.estado == EstadoOrden.PAGADA).order_by(Orden.id_orden.desc()).all()
    
    row_idx = 5
    for ord_obj in ordenes:
        # Detalles de productos concatenados
        items_str = ", ".join([f"{item.cantidad}x {item.producto.nombre if item.producto else 'Item'}" for item in ord_obj.items])
        
        # Método de pago
        pago_str = ord_obj.pagos[0].metodo_pago.value if ord_obj.pagos else "N/A"
        fecha_str = ord_obj.fecha_cierre.strftime("%d/%m/%Y %H:%M") if ord_obj.fecha_cierre else ord_obj.fecha_creacion.strftime("%d/%m/%Y %H:%M")
        bartender_str = ord_obj.usuario_creacion.nombre if ord_obj.usuario_creacion else "Desconocido"
        
        ws1.cell(row=row_idx, column=1, value=f"#{ord_obj.id_orden:05d}").alignment = Alignment(horizontal="center")
        ws1.cell(row=row_idx, column=2, value=fecha_str).alignment = Alignment(horizontal="center")
        ws1.cell(row=row_idx, column=3, value=ord_obj.numero_mesa).alignment = Alignment(horizontal="left")
        ws1.cell(row=row_idx, column=4, value=bartender_str).alignment = Alignment(horizontal="left")
        ws1.cell(row=row_idx, column=5, value=items_str).alignment = Alignment(horizontal="left")
        ws1.cell(row=row_idx, column=6, value=pago_str).alignment = Alignment(horizontal="center")
        
        tot_cell = ws1.cell(row=row_idx, column=7, value=float(ord_obj.total))
        tot_cell.number_format = 'Q #,##0.00'
        tot_cell.alignment = Alignment(horizontal="right")
        
        for c in range(1, 8):
            ws1.cell(row=row_idx, column=c).border = cell_border
            ws1.cell(row=row_idx, column=c).font = cell_font
            
        row_idx += 1
        
    # Fila de totales
    if row_idx > 5:
        ws1.cell(row=row_idx, column=6, value="TOTAL GENERAL:").font = bold_cell_font
        ws1.cell(row=row_idx, column=6).alignment = Alignment(horizontal="right")
        tot_gen = ws1.cell(row=row_idx, column=7, value=f"=SUM(G5:G{row_idx-1})")
        tot_gen.font = bold_cell_font
        tot_gen.number_format = 'Q #,##0.00'
        tot_gen.border = header_border

    # ==============================================================
    # HOJA 2: Rendimiento Bartenders
    # ==============================================================
    ws2 = wb.create_sheet(title="Rendimiento Bartenders")
    ws2.views.sheetView[0].showGridLines = True
    
    ws2["A1"] = "BOURLEMONT CHAMPAGNE BAR"
    ws2["A1"].font = title_font
    ws2["A2"] = "Métricas de Rendimiento y Ventas por Bartender"
    ws2["A2"].font = sub_font
    
    headers2 = ["Bartender", "Órdenes Atendidas", "Total Vendido (Q)", "Ticket Promedio (Q)"]
    row_idx = 4
    for col_idx, h in enumerate(headers2, start=1):
        cell = ws2.cell(row=row_idx, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = header_border
        
    bartenders = db.query(Usuario).all()
    row_idx = 5
    for b in bartenders:
        # Calcular órdenes pagadas atendidas
        ords_b = [o for o in b.ordenes_creadas if o.estado == EstadoOrden.PAGADA]
        cant_ords = len(ords_b)
        total_b = sum([float(o.total) for o in ords_b])
        ticket_prom = (total_b / cant_ords) if cant_ords > 0 else 0.0
        
        ws2.cell(row=row_idx, column=1, value=b.nombre).alignment = Alignment(horizontal="left")
        ws2.cell(row=row_idx, column=2, value=cant_ords).alignment = Alignment(horizontal="center")
        
        c3 = ws2.cell(row=row_idx, column=3, value=total_b)
        c3.number_format = 'Q #,##0.00'
        c3.alignment = Alignment(horizontal="right")
        
        c4 = ws2.cell(row=row_idx, column=4, value=ticket_prom)
        c4.number_format = 'Q #,##0.00'
        c4.alignment = Alignment(horizontal="right")
        
        for c in range(1, 5):
            ws2.cell(row=row_idx, column=c).border = cell_border
            ws2.cell(row=row_idx, column=c).font = cell_font
            
        row_idx += 1

    # ==============================================================
    # HOJA 3: Consumo Insumos y Proyección
    # ==============================================================
    ws3 = wb.create_sheet(title="Consumo Insumos y Proyección")
    ws3.views.sheetView[0].showGridLines = True
    
    ws3["A1"] = "BOURLEMONT CHAMPAGNE BAR"
    ws3["A1"].font = title_font
    ws3["A2"] = "Control Algorítmico de Escandallos, Consumo en ml y Proyección de Botellas"
    ws3["A2"].font = sub_font
    
    headers3 = [
        "Insumo / Licor Base",
        "Total Consumido (ml)",
        "Botellas Consumidas (750ml)",
        "Stock Remanente (ml)",
        "Stock Mínimo (ml)",
        "Estado Reabastecimiento"
    ]
    
    row_idx = 4
    for col_idx, h in enumerate(headers3, start=1):
        cell = ws3.cell(row=row_idx, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = header_border
        
    # Obtener todos los productos que son insumos o licores
    insumos = db.query(Producto).all()
    
    # Calcular consumo total histórico o por órdenes pagadas
    consumo_map = {}
    for ord_obj in ordenes:
        for item in ord_obj.items:
            recetas = db.query(RecetaEscandallo).filter(RecetaEscandallo.id_producto_final == item.id_producto).all()
            if recetas:
                for r in recetas:
                    consumo_map[r.id_insumo_base] = consumo_map.get(r.id_insumo_base, 0) + (item.cantidad * r.cantidad_descontar_ml)
            else:
                # Venta directa
                ml_u = 750 if "botella" in item.producto.nombre.lower() or item.producto.categoria.value == "CHAMPAGNE" else 45
                consumo_map[item.id_producto] = consumo_map.get(item.id_producto, 0) + (item.cantidad * ml_u)
                
    row_idx = 5
    for p in insumos:
        ml_cons = consumo_map.get(p.id_producto, 0)
        botellas_eq = round(ml_cons / 750.0, 2)
        
        ws3.cell(row=row_idx, column=1, value=f"{p.nombre} ({p.categoria.value})").alignment = Alignment(horizontal="left")
        
        c_cons = ws3.cell(row=row_idx, column=2, value=ml_cons)
        c_cons.number_format = '#,##0 "ml"'
        c_cons.alignment = Alignment(horizontal="right")
        
        c_bot = ws3.cell(row=row_idx, column=3, value=botellas_eq)
        c_bot.number_format = '#,##0.00 "bot"'
        c_bot.alignment = Alignment(horizontal="right")
        
        c_stk = ws3.cell(row=row_idx, column=4, value=p.stock_ml)
        c_stk.number_format = '#,##0 "ml"'
        c_stk.alignment = Alignment(horizontal="right")
        
        c_min = ws3.cell(row=row_idx, column=5, value=p.stock_minimo_ml)
        c_min.number_format = '#,##0 "ml"'
        c_min.alignment = Alignment(horizontal="right")
        
        # Fórmula Excel para Estado de reabastecimiento: SI(D5<=E5; "⚠️ REORDENAR"; "OK")
        estado_formula = f'=IF(D{row_idx}<=E{row_idx}, "⚠️ REORDENAR", "OK OPTIMO")'
        c_est = ws3.cell(row=row_idx, column=6, value=estado_formula)
        c_est.alignment = Alignment(horizontal="center")
        if p.stock_ml <= p.stock_minimo_ml:
            c_est.font = Font(name="Segoe UI", size=10, bold=True, color="C0392B")
            c_est.fill = PatternFill(start_color="FDEDEC", end_color="FDEDEC", fill_type="solid")
        else:
            c_est.font = Font(name="Segoe UI", size=10, color="27AE60")
            
        for c in range(1, 7):
            ws3.cell(row=row_idx, column=c).border = cell_border
            if c != 6:
                ws3.cell(row=row_idx, column=c).font = cell_font
                
        row_idx += 1

    # Autoajuste de ancho de columnas para todas las hojas
    for ws in [ws1, ws2, ws3]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or '')
                if not val.startswith("="):
                    max_len = max(max_len, len(val))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)
            
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream
