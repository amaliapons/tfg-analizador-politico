from fpdf import FPDF

def generar_pdf(partido, ano, porcentaje, texto_analisis):
    pdf = FPDF()
    
    # márgenes a 25 milímetros
    pdf.set_margins(left=25, top=20, right=25)
    pdf.add_page()
    
    # margen inferior para los saltos de página
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # Título
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"Análisis de Coherencia: {partido.upper()} ({ano})", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)
    
    # Porcentaje
    pdf.set_font("helvetica", "B", 14)
    if porcentaje < 50:
        veredicto_corto = "Contradicción o Ausencia"
    elif porcentaje < 85:
        veredicto_corto = "Coherencia Parcial"
    else:
        veredicto_corto = "Alineación Total"
        
    pdf.cell(0, 10, f"Veredicto: {porcentaje}% - {veredicto_corto}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Texto del análisis de la IA
    pdf.set_font("helvetica", "", 12)
    pdf.multi_cell(0, 8, texto_analisis)
    
    # Marca IA
    pdf.ln(10) 
    pdf.set_font("helvetica", "I", 9) 
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 10, "Este informe ha sido generado automáticamente por un sistema de Inteligencia Artificial.", new_x="LMARGIN", new_y="NEXT", align='C')
    
    return bytes(pdf.output())