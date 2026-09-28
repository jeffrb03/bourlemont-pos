from datetime import datetime
from app.models.models import Orden, TransaccionPago, FacturaFEL
from app.core.config import settings

def generar_ticket_termico(orden: Orden, pago: TransaccionPago, fel: FacturaFEL = None) -> str:
    """
    Genera la cadena de impresión para impresora térmica de 80mm (48 columnas).
    """
    ancho = 42
    linea = "=" * ancho
    linea_delgada = "-" * ancho
    
    fecha_str = orden.fecha_cierre.strftime("%d/%m/%Y %H:%M:%S") if orden.fecha_cierre else datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    bartender_name = orden.usuario_creacion.nombre if orden.usuario_creacion else "BARTENDER"
    
    subtotal_sin_iva = float(orden.total) / (1 + settings.DEFAULT_TAX_RATE)
    iva = float(orden.total) - subtotal_sin_iva
    
    ticket = []
    ticket.append(linea)
    ticket.append("       BOURLEMONT CHAMPAGNE BAR       ".center(ancho))
    ticket.append("    Exclusividad & Alta Coctelería    ".center(ancho))
    ticket.append("     Ciudad Vieja, Sacatepéquez       ".center(ancho))
    ticket.append("         NIT: 98765432-1              ".center(ancho))
    ticket.append(linea)
    ticket.append(f"ORDEN #{orden.id_orden:05d}   |   {orden.numero_mesa}")
    ticket.append(f"Fecha: {fecha_str}")
    ticket.append(f"Atendió: {bartender_name}")
    
    if fel and fel.nit_receptor:
        ticket.append(f"Cliente: {fel.nombre_receptor}")
        ticket.append(f"NIT: {fel.nit_receptor}")
    else:
        ticket.append("Cliente: CONSUMIDOR FINAL")
        ticket.append("NIT: CF")
        
    ticket.append(linea_delgada)
    ticket.append("CANT  DESCRIPCIÓN             TOTAL (Q)")
    ticket.append(linea_delgada)
    
    for item in orden.items:
        prod_name = item.producto.nombre if item.producto else f"Prod {item.id_producto}"
        if len(prod_name) > 23:
            prod_name = prod_name[:20] + "..."
        precio_str = f"{float(item.subtotal):.2f}"
        cant_str = f"{item.cantidad:2d}x"
        col_espacio = ancho - len(cant_str) - len(precio_str) - 2
        ticket.append(f"{cant_str} {prod_name.ljust(col_espacio)} Q{precio_str.rjust(7)}")
        
    ticket.append(linea_delgada)
    ticket.append(f"SUBTOTAL (Sin IVA):       Q {subtotal_sin_iva:>9.2f}")
    ticket.append(f"IVA (12%):                Q {iva:>9.2f}")
    ticket.append(f"TOTAL CUENTA:             Q {float(orden.total):>9.2f}")
    
    if pago.propina > 0:
        ticket.append(f"PROPINA VOLUNTARIA:       Q {float(pago.propina):>9.2f}")
        gran_total = float(orden.total) + float(pago.propina)
        ticket.append(f"TOTAL CON PROPINA:        Q {gran_total:>9.2f}")
        
    ticket.append(linea_delgada)
    ticket.append(f"MÉTODO DE PAGO: {pago.metodo_pago.value}")
    ticket.append(f"PAGADO: Q {float(pago.monto_pagado):.2f}")
    
    ticket.append(linea)
    if fel and fel.uuid_autorizacion:
        ticket.append("       DOCUMENTO TRIBUTARIO FEL       ".center(ancho))
        ticket.append(f"Serie: {fel.serie} | No: {fel.numero_dte}")
        ticket.append("Autorización SAT:")
        ticket.append(f"{fel.uuid_autorizacion}".center(ancho))
        ticket.append(f"Certificación: {fel.fecha_certificacion}")
    elif fel and fel.estado_certificacion.value == "ERROR_OFFLINE":
        ticket.append("   EMISIÓN EN CONTINGENCIA OFFLINE    ".center(ancho))
        ticket.append("     Sujeto a certificación SAT       ".center(ancho))
    else:
        ticket.append("   COMPROBANTE DE VENTA INTERNA       ".center(ancho))
        
    ticket.append(linea)
    ticket.append("  ¡Gracias por su distinguida visita! ".center(ancho))
    ticket.append("      Bourlemont Champagne Bar        ".center(ancho))
    ticket.append(linea)
    ticket.append("\n\n")
    
    return "\n".join(ticket)
