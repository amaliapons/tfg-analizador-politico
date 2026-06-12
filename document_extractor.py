import re

# PROPOSICIONES NO DE LEY (PNL)

def extract_pnl_by_party(texto_completo_pdf: str, partido: str = "grupo parlamentario popular") -> str:
    """
    Extrae la primera iniciativa del partido especificado que encuentre en el documento.
    Función para hacer pruebas rápidas de funcionamiento.
    """
    if not texto_completo_pdf:
        return ""

    trozos_iniciativas = re.split(r'\b\d{3}/\d{6}\b', texto_completo_pdf)
    texto_extraido = ""
    partido_objetivo = partido.lower()
    
    for trozo in trozos_iniciativas:
        texto_minusculas = trozo.lower()
        
        # Comprobar que mencione al partido y que sea un texto largo (no el índice)
        if partido_objetivo in texto_minusculas and len(trozo) > 1500: 
            texto_extraido = trozo.strip()
            break 
            
    return texto_extraido


def extract_pnl_by_id(texto_completo_pdf: str, id_expediente: str) -> str:
    """
    Busca y extrae una iniciativa parlamentaria concreta usando su número 
    de expediente exacto (ej: '162/001213').
    """
    if not texto_completo_pdf:
        return ""

    trozos_iniciativas = re.split(r'\b\d{3}/\d{6}\b', texto_completo_pdf)
    ids_encontrados = re.findall(r'\b\d{3}/\d{6}\b', texto_completo_pdf)
    texto_extraido = ""
    
    for i, id_actual in enumerate(ids_encontrados):
        if id_actual == id_expediente:
            # Seleccionar el trozo de texto correspondiente a ese ID
            # El +1 es porque el primer trozo (índice 0) es la portada del PDF
            if (i + 1) < len(trozos_iniciativas):
                posible_texto = trozos_iniciativas[i + 1].strip()
                
                # Solo guardar si tiene más de 1500 caracteres
                if len(posible_texto) > 1500:
                    texto_extraido = posible_texto
                    break 
            
    return texto_extraido


# ENMIENDAS

def extract_amendment_by_number(texto_completo_pdf: str, num_enmienda: str) -> str:
    """
    Busca y extrae una enmienda parlamentaria concreta usando su número exacto.
    Detecta patrones como 'Enmienda núm. 45' o 'Enmienda número 45'.
    """
    if not texto_completo_pdf:
        return ""

    # El patrón busca la palabra Enmienda, seguida de "núm." o "número", y luego dígitos
    patron_corte = r'Enmienda\s+(?:núm\.|número)\s+\d+'
    
    # Cortar el texto y extraer las etiquetas
    trozos = re.split(patron_corte, texto_completo_pdf, flags=re.IGNORECASE)
    etiquetas = re.findall(patron_corte, texto_completo_pdf, flags=re.IGNORECASE)
    
    texto_extraido = ""
    
    patron_numero_exacto = rf'\b{num_enmienda}\b'
    
    for i, etiqueta in enumerate(etiquetas):
        if re.search(patron_numero_exacto, etiqueta):
            if (i + 1) < len(trozos):
                posible_texto = trozos[i + 1].strip()
                
                if len(posible_texto) > 50:
                    # Volver a pegar el título
                    texto_extraido = etiqueta.strip() + "\n" + posible_texto
                    break 
            
    return texto_extraido



# PROPOSICIONES DE LEY (PdL)

def extract_full_pdl(texto_completo_pdf: str) -> str:
    """
    Extrae el texto de una Proposición/Proyecto de Ley usando la 
    'Exposición de motivos', saltándose la portada y rescatando el Título
    """
    if not texto_completo_pdf:
        return ""
    
    # Buscar el inicio de la ley. 
    patron_inicio = r'Exposición\s+de\s+motivos'

    partes = re.split(patron_inicio, texto_completo_pdf, maxsplit=1, flags=re.IGNORECASE)

    if len(partes) > 1:
        portada = partes[0]
        texto_principal = partes[1]
        
        # Recuperar el título buscando la última aparición de "Proposición/Proyecto de Ley"
        patron_titulo = r'.*((?:Proposición|Proyecto)\s+de\s+ley.*)'
        match = re.search(patron_titulo, portada, flags=re.IGNORECASE | re.DOTALL)
        
        if match:
            # Recuperar el título
            titulo = match.group(1).strip()
        else:
            # Si no lo encuentra -> título genérico
            titulo = "Iniciativa Legislativa"
            
        # Unir Título + etiqueta de Exposición de motivos + texto
        texto_extraido = f"{titulo}\n\nExposición de motivos\n{texto_principal.strip()}"
        return texto_extraido
    else:
        # Si no hay Exposición de motivos, no es una PdL
        return ""



# DIARIOS DE SESIONES

def extract_speech(texto_completo_pdf: str, orador: str) -> str:
    """
    Extrae todas las intervenciones de un orador en un Diario de Sesiones
    ignorando las interrupciones desde los escaños.
    """
    if not texto_completo_pdf:
        return ""
    
    # Partir el texto cada vez que el orador habla
    # Si el usuario ha metido un paréntesis en el nombre, lo escapamos
    orador_seguro = re.escape(orador)
    fragmentos = re.split(orador_seguro, texto_completo_pdf)
    
    if len(fragmentos) < 2:
        return "" # No se encontró al orador
    
    discurso_completo = ""
    
    # El patrón del siguiente orador principal (ignora interrupciones)
    # "El señor" o "La señora" + espacio + al menos 2 letras mayúsculas seguidas
    patron_siguiente_orador = r'(?:La señora|El señor)\s+[A-ZÁÉÍÓÚÑÇ]{2,}'
    
    # Recorrer todos los momentos en los que habló el orador
    # Empezamos en el índice 1 porque el índice 0 es el texto antes de que hablara por primera vez
    for i, fragmento in enumerate(fragmentos[1:]):
        
        # Cortar su discurso cuando detecte el patrón del siguiente orador principal
        cortes = re.split(patron_siguiente_orador, fragmento, maxsplit=1)
        
        # Limpiar el texto de esa intervención
        intervencion_limpia = cortes[0].strip()
        
        # Añadir al texto final con un separador
        discurso_completo += f"--- INTERVENCIÓN {i+1} ---\n"
        discurso_completo += intervencion_limpia + "\n\n"
        
    return discurso_completo.strip()