import re

def clean_parliamentary_text(text: str) -> str:
    """
    Función para limpiar los artefactos de texto extraídos de PDFs del BOE/BOCG.
    """
    if not text:
        return ""

    # Unir palabras separadas por guiones a final de línea
    clean_text = re.sub(r'-\s*\n\s*', '', text)

    # Eliminar los saltos de línea que rompen los párrafos por la mitad
    clean_text = clean_text.replace('\n', ' ')

    # DOCUMENTOS 2015 - Actualidad
    clean_text = re.sub(r'CONGRESO DE LOS DIPUTADOS.*?Serie [A-Z].*?Pág\.\s*\d+\s*BOLETÍN OFICIAL DE LAS CORTES GENERALES', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'DIARIO DE SESIONES DEL CONGRESO DE LOS DIPUTADOS.*?Pág\.\s*\d+', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'Núm\.\s*\d+\s+(?:Pág\.|Página)\s*:?\s*\d+', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'BOLETÍN OFICIAL DE LAS CORTES GENERALES\s*SENADO.*?\d{4}', '', clean_text, flags=re.IGNORECASE) 
    patron_encabezado = r'(?:BOCG\.|BOLETÍN OFICIAL DE LAS CORTES GENERALES|BOLETÍN OFICIAL DEL ESTADO).*?(?:Pág\.|Página)\s*:?\s*\d+'
    clean_text = re.sub(patron_encabezado, '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'cve:\s*BOCG[^\s]*', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'https?://(?:www\.)?(?:senado|congreso)\.es.*?(?:S\.C\.E\.|Teléf\.:[\s\d]+)', '', clean_text, flags=re.IGNORECASE) 
    clean_text = re.sub(r'Edición electrónica preparada por.*?https?://(?:www\.)?boe\.es', '', clean_text, flags=re.IGNORECASE)   
    


    # DOCUMENTOS ANTERIORES
    # Cabeceras intercaladas 
    clean_text = re.sub(r'(?:[IVX]+\s+LEGISLATURA\s+)?Serie\s+[A-Z].*?Presentada\s+por\s+el\s+Grupo\s+Parlamentario.*?\.', ' ', clean_text, flags=re.IGNORECASE)
    
    # Pies de página intercalados 
    clean_text = re.sub(r'Congreso\s+\d{1,2}\s+de\s+[a-z]+\s+de\s+\d{4}\.—Serie\s+[A-Z]\.\s+Núm\.\s+[\d\-]+\s+\d+', ' ', clean_text, flags=re.IGNORECASE)
    
    # Imprenta final antigua 
    clean_text = re.sub(r'Edita:\s*Congreso\s+de\s+los\s+Diputados.*', '', clean_text, flags=re.IGNORECASE)

    # Eliminar espacios en blanco múltiples
    clean_text = re.sub(r'\s+', ' ', clean_text)

    # Quitar espacios al principio y al final del texto
    return clean_text.strip()
