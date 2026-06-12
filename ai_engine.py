import os
import json
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


# Cargar API Key de OpenAI desde .env
load_dotenv()

def analizar_coherencia(texto_iniciativa: str, partido: str, ano: str, postura: str) -> str:
    """
    Coge el texto de una iniciativa parlamentaria, busca contexto en el programa
    electoral y le pide a OpenAI que analice la coherencia.
    """
    if not texto_iniciativa:
        return "Error: No hay texto para analizar."
    
    # Formatear el nombre combinando partido y año
    partido_limpio = partido.lower().replace(" ", "_")
    ano_limpio = ano.lower()
    nombre_carpeta = f"db_{partido_limpio}_{ano_limpio}"

    # Comprobar que la base de datos existe
    if not os.path.exists(nombre_carpeta):
        return f"Error: No existe base de datos para {partido} del año {ano}."

    # Configurar el modelo de OpenAI 
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    
    # Query Rewriting
    prompt_extraccion = (
        "Extrae las 4 o 5 palabras clave más importantes del siguiente texto legislativo para buscar en un programa electoral. "
        "Concéntrate en el tema material (ej: ganadería, mundo rural, impuestos, sanidad) y omite el formato legal "
        "(ej: proposición de ley, plan nacional, gobierno, instar, decreto).\n"
        "Devuelve solo las palabras clave separadas por comas, sin introducciones:\n\n"
        f"{texto_iniciativa}"
    )
    palabras_clave = llm.invoke(prompt_extraccion).content
    
    # Conectar a la Base de Datos Vectorial del partido seleccionado 
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(persist_directory=nombre_carpeta, embedding_function=embeddings)
    
    # Retrieve
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(palabras_clave)

    # Extraer metadatos
    fragmentos_con_pagina = []
    for doc in docs:
        if 'page' in doc.metadata:
            num_pagina = doc.metadata['page'] + 1 # Corrección de pág
        else:
            num_pagina = 'Desconocida'
        texto_chunk = f"--- EXTRAÍDO DE LA PÁGINA {num_pagina} ---\n{doc.page_content}"
        fragmentos_con_pagina.append(texto_chunk)
        
    contexto_programa = "\n\n".join(fragmentos_con_pagina)

    # Mostrar por terminal lo que ChromaDB ha recuperado
    #print("\n" + "="*50)
    #print(f"FRAGMENTOS RECUPERADOS PARA: {partido.upper()}")
    #print("="*50)
    #print(contexto_programa)
    #print("="*50 + "\n")
    
    
    # Diseño de Prompt

    # Instrucciones de la IA según si hay votación o es un discurso
    
    if postura == "No aplica (Es un discurso)":
        instruccion_contexto = "TIPO DE ANÁLISIS: DISCURSO. Evalúa si la postura del orador es coherente con el programa."
        regla_puntuacion = (
            "Elige uno de estos valores, sé minucioso en el análisis y ten en cuenta cualquier matiz:\n"
            "100%: El discurso defiende activamente el punto del programa usando argumentos, premisas y conceptos idénticos o equivalentes."
            " No hay ningún tipo de matiz o cambio de tono respecto al programa.\n"
            "75%: El orador defiende el objetivo general del programa, pero introduce matices, excusas o condiciones que no estaban en el texto original"
            " (ej. 'Lo haremos, pero solo cuando la situación macroeconómica lo permita' o 'depende de Europa').\n"
            "50%: Ante una interpelación sobre una promesa del programa, el orador cambia de tema, ataca al oponente político"
            " o usa generalidades sin reafirmar ni negar la medida. (ej. 'y tú más').\n"
            "25%: El discurso asume premisas que van en contra del programa, pero sin atacar la promesa directamente."
            " (ej. El programa pide bajar impuestos, pero en el discurso el político defiende que es momento de sostener los servicios públicos mediante el esfuerzo fiscal).\n"
            "0%: El orador afirma explícitamente que la promesa del programa fue un error,"
            " que la realidad ha cambiado y no es viable, o defiende retóricamente exactamente lo contrario a lo escrito.\n"
        )

    elif postura == "Abstención":
        instruccion_contexto = "TIPO DE ANÁLISIS: VOTACIÓN. El partido votó: Abstención."
        regla_puntuacion = (
            "REGLA PARA ABSTENCIÓN: Al abstenerse, el partido ni apoya ni bloquea. "
            "Elige estrictamente uno de estos dos valores:\n"
            "   - Si la iniciativa coincide con su programa (deberían haber votado a favor): Asigna 50 (Incoherencia por omisión / Falta de apoyo).\n"
            "   - Si la iniciativa va en contra de su programa (deberían haber votado en contra): Asigna 25 (Pasividad cómplice / Fricción grave).\n"
            "   - Si el programa es ambiguo (es vago y no se puede afirmar ni SÍ ni NO con rotundidad ): Asigna 50.\n\n"
        )
    
    else:
        instruccion_contexto = f"TIPO DE ANÁLISIS: VOTACIÓN. El partido votó: {postura.upper()}."
        regla_puntuacion = (
        "Evalúa internamente estas 3 variables con SÍ o NO:\n"
        "   - V1 (Objetivo): ¿La iniciativa persigue el mismo objetivo y se defiende/vota a favor?\n"
        "   - V2 (Alcance/Sujetos): ¿La iniciativa afecta a los mismos beneficiarios/territorios/plazos sin exclusiones?\n"
        "   - V3 (Mecanismo): ¿La herramienta legal o económica es exactamente la misma prometida?\n\n"
        "RÚBRICA INTERNA:\n"
        "   - V1=SÍ, V2=SÍ, V3=SÍ  -> 100 (Identidad total. Promesa cumplida sin ningún matiz).\n"
        "   - V1=SÍ, V2=NO, V3=SÍ  -> 80 (Cambio de alcance. Cumplen objetivo y método, pero a otra escala).\n"
        "   - V1=SÍ, V2=SÍ, V3=NO  -> 70 (Cambio de método. Cumplen objetivo y alcance, pero con otra herramienta).\n"
        "   - V1=SÍ, V2=NO, V3=NO  -> 60 (Coherencia parcial. Solo coinciden en el espíritu general).\n"
        "   - Programa Ambiguo     -> 50 (El texto recuperado no permite confirmar ni SÍ ni NO).\n"
        "   - V1=NO (Fricción)     -> 25 (Votan algo que entorpece o retrasa el programa, pero sin ser una línea roja).\n"
        "   - V1=NO (Oposición)    -> 0 (Contradicción directa. Votan en contra de su promesa o defienden lo contrario).\n\n"
        )


    system_prompt = (
        "Eres un auditor experto y determinista de coherencia política. Tu tarea es contrastar el programa electoral "
        "de un partido con una iniciativa parlamentaria.\n\n"
        f"{instruccion_contexto}\n\n"
        f"{regla_puntuacion}"
        "REGLAS DE RIGOR Y VOCABULARIO:\n"
        "1. VOCABULARIO: No uses términos técnicos internos como 'Dimensión', 'Variables' o 'V1(Objetivo Núcleo)'/'V2(Alcance/Sujetos)'/'V3(Mecanismo)'. "
        "Escribe de forma natural para el ciudadano.\n"
        "2. CERO INVENCIÓN: Basa tu análisis exclusivamente en los textos proporcionados. No asumas posturas del partido que no estén en el texto.\n"
        "Busca información externa únicamente en el caso de necesitar comprender el contexto de una ley no explícita en los textos proporcionados.\n"
        "ESTRUCTURA DE LA RESPUESTA AL USUARIO:\n"
        "1. RESUMEN: Explica en 2 o 3 líneas de qué trata la iniciativa analizada\n"
        "2. PROMESA ELECTORAL: Explica en 2 o 3 líneas qué decía el partido sobre este tema exacto en su programa. "
        "MENCIONA explícitamente entre paréntesis de qué página o páginas procede dicha información (ej: Pág. 42).\n"
        "3. VEREDICTO DE COHERENCIA: Justifica tu veredicto de forma minuciosa.\n\n"
        "Al final del todo, en una nueva línea, escribe ÚNICAMENTE la etiqueta [PORCENTAJE: X] "
        "(donde X debe ser uno de los números exactos de la rúbrica: 100, 80, 70, 60, 50, 25 o 0). "
        "NO escribas nada más después de la etiqueta.\n\n"
        f"CONTEXTO DEL PROGRAMA ELECTORAL (CON PÁGINAS):\n{contexto_programa}"
    )

    #Cadena RAG

    mensajes = [
        ("system", system_prompt),
        ("human", f"INICIATIVA A ANALIZAR:\n\n{texto_iniciativa}")
    ]
    
    respuesta = llm.invoke(mensajes)
    
    return respuesta.content



def explicar_documento(texto_iniciativa: str) -> dict:
    """
    Coge un texto parlamentario complejo y lo traduce un lenguaje más sencillo.
    Devuelve un diccionario de Python (utilizando JSON) con las claves:
    'impacto', 'resumen' y 'diccionario'.
    """
    if not texto_iniciativa:
        return {"error": "No hay texto para analizar."}

    # Inicializar el modelo
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    
    system_prompt = (
        "Eres un experto en comunicación clara, Simplificación Lingüística y accesibilidad cognitiva. "
        "Tu objetivo es traducir textos parlamentarios burocráticos a un lenguaje claro, "
        "fácil de entender para cualquier persona sin conocimientos de política.\n\n"
        "Analiza el siguiente texto y devuelve EXCLUSIVAMENTE un objeto JSON válido con esta estructura exacta:\n"
        "{\n"
        "  \"impacto\": \"Explica en 2 o 3 líneas a qué grupo de personas afecta esta medida y cómo afecta a su día a día (dinero, derechos, obligaciones). Usa viñetas o emojis si es útil.\",\n"
        "  \"idea_principal\": \"Un resumen muy corto (máximo 2 o 3 frases) directo explicando el núcleo de la propuesta.\",\n"
        "  \"diccionario\": {\n"
        "    \"Término Complejo 1\": \"Explicación didáctica y accesible.\",\n"
        "    \"Término Complejo 2\": \"Explicación didáctica y accesible.\"\n"
        "  }\n"
        "}\n\n"
        "REGLAS ESTRICTAS:\n"
        "1. NO uses lenguaje burocrático ('Proposición no de ley', 'Disposición derogatoria', etc.).\n"
        "2. El diccionario debe contener exactamente entre 2 y 4 términos complejos o ambiguos que aparezcan en el texto.\n"
        "3. Tu respuesta debe ser ÚNICA y EXCLUSIVAMENTE el JSON en texto plano. No incluyas bloques de código markdown (```json), ni introducciones."
    )
    
    # Preparar el mensaje
    mensajes = [
        ("system", system_prompt),
        ("human", f"Texto parlamentario a traducir:\n\n{texto_iniciativa}")
    ]
    
    # Llamar a la IA
    respuesta = llm.invoke(mensajes)
    
    # Limpieza
    contenido = respuesta.content.strip()
    if contenido.startswith("```json"):
        contenido = contenido[7:]
    if contenido.endswith("```"):
        contenido = contenido[:-3]
    contenido = contenido.strip()

    # Convertir JSON a Diccionario de Python
    try:
        resultado = json.loads(contenido)
        return resultado
    except json.JSONDecodeError:
        # Por si la IA se equivoca con alguna comilla y el JSON se rompe
        return {
            "error": True,
            "mensaje": "La IA ha devuelto un formato incorrecto. Por favor, vuelve a intentarlo."
        }
    

def explorar_programa(partido: str, ano: str, tema: str) -> dict:
    """
    Busca un tema específico en el programa electoral de un partido y un año concretos.
    Devuelve un diccionario con la postura general, medidas clave, cita y página de origen.
    """
    if not tema.strip():
        return {"error": "Por favor, escribe un tema para buscar."}

    partido_limpio = partido.lower().replace(" ", "_")
    ano_limpio = ano.lower()
    nombre_carpeta = f"db_{partido_limpio}_{ano_limpio}"
    
    # Comprobar si hay base de datos de ese programa
    if not os.path.exists(nombre_carpeta):
        return {"error": f"⚠️ Aún no existe una base de datos para el programa de {partido.upper()} del año {ano}."}

    # Retrieval
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(persist_directory=nombre_carpeta, embedding_function=embeddings)
    
    # 5 fragmentos más relevantes sobre ese tema
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(tema)

    # Inyectar metadatos al contexto
    fragmentos_con_pagina = []
    for doc in docs:
        if 'page' in doc.metadata:
            num_pagina = doc.metadata['page'] + 1
        else:
            num_pagina = 'Desconocida'
            
        texto = f"--- EXTRAÍDO DE LA PÁGINA {num_pagina} ---\n{doc.page_content}"
        fragmentos_con_pagina.append(texto)
        
    contexto = "\n\n".join(fragmentos_con_pagina)

    # Augmented Generation
    system_prompt = (
        f"Eres un analista político neutral y riguroso. Tu objetivo es explicar de forma muy clara "
        f"cuál es la postura y las promesas del partido {partido.upper()} sobre el tema: '{tema}'.\n\n"
        "Te voy a proporcionar fragmentos recuperados de su programa electoral junto con la página de donde proceden. "
        "Basándote ÚNICAMENTE en esos textos, devuelve EXCLUSIVAMENTE un objeto JSON válido con esta estructura exacta:\n"
        "{\n"
        "  \"postura_general\": \"Un resumen de 2 o 3 frases sobre su visión general de este tema.\",\n"
        "  \"medidas_clave\": [\"Medida concreta 1\", \"Medida concreta 2\", \"Medida concreta 3\"],\n"
        "  \"cita_destacada\": \"Una frase corta y literal entrecomillada extraída del texto que sea representativa.\",\n"
        "  \"pagina_cita\": \"El número de la página de donde has sacado la cita_destacada (solo escribe el número).\"\n"
        "}\n\n"
        "REGLAS ESTRICTAS:\n"
        "1. Si los fragmentos NO mencionan este tema, escribe en 'postura_general' que no hay menciones relevantes y deja la lista vacía.\n"
        "2. NO te inventes medidas políticas ni números de página. Solo puedes usar la información de los fragmentos.\n"
        "3. Devuelve ÚNICA y EXCLUSIVAMENTE el JSON, sin comillas markdown de código (```json)."
    )
    
    mensajes = [
        ("system", system_prompt),
        ("human", f"Contexto extraído del programa de {partido.upper()}:\n\n{contexto}")
    ]
    
    respuesta = llm.invoke(mensajes)
    
    # Limpiar y empaquetar el JSON
    contenido = respuesta.content.strip()
    if contenido.startswith("```json"):
        contenido = contenido[7:]
    if contenido.endswith("```"):
        contenido = contenido[:-3]
    contenido = contenido.strip()

    try:
        resultado = json.loads(contenido)
        return resultado
    except json.JSONDecodeError:
        return {
            "error": "La IA ha devuelto un formato incorrecto. Por favor, vuelve a intentarlo."
        }
    

def comparar_programas(partido: str, ano_a: str, ano_b: str, tema: str) -> dict:
    """
    Realiza un RAG múltiple buscando en dos bases de datos distintas.
    Compara los contextos y devuelve un JSON con el análisis de la evolución política.
    """
    if not tema.strip():
        return {"error": "Por favor, escribe un tema para buscar."}

    partido_limpio = partido.lower().replace(" ", "_")
    carpeta_a = f"db_{partido_limpio}_{ano_a.lower()}"
    carpeta_b = f"db_{partido_limpio}_{ano_b.lower()}"
    
    # Comprobar que existan las bases de datos
    if not os.path.exists(carpeta_a):
        return {"error": f"⚠️ No existe base de datos de {partido.upper()} del año {ano_a}."}
    if not os.path.exists(carpeta_b):
        return {"error": f"⚠️ No existe base de datos de {partido.upper()} del año {ano_b}."}

    # Doble Retrieval
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    embeddings = OpenAIEmbeddings()
    
    # Extraer del Año A
    vectorstore_a = Chroma(persist_directory=carpeta_a, embedding_function=embeddings)
    retriever_a = vectorstore_a.as_retriever(search_kwargs={"k": 4}) # 4 párrafos del año A
    docs_a = retriever_a.invoke(tema)
    contexto_a = "\n\n".join([doc.page_content for doc in docs_a])

    # Extraer del Año B
    vectorstore_b = Chroma(persist_directory=carpeta_b, embedding_function=embeddings)
    retriever_b = vectorstore_b.as_retriever(search_kwargs={"k": 4}) # 4 párrafos del año B
    docs_b = retriever_b.invoke(tema)
    contexto_b = "\n\n".join([doc.page_content for doc in docs_b])

    # RAG Comparativa
    system_prompt = (
        f"Eres un analista político neutral y experto en hemeroteca. Tu objetivo es comparar la evolución de las promesas del partido {partido.upper()} "
        f"sobre el tema '{tema}' entre el año {ano_a} y el año {ano_b}.\n\n"
        "Te voy a proporcionar fragmentos recuperados de sus programas electorales de ambos años. "
        "Devuelve EXCLUSIVAMENTE un objeto JSON válido con esta estructura exacta:\n"
        "{\n"
        "  \"resumen_evolucion\": \"Explicación de 2 o 3 frases sobre cómo ha cambiado o se ha mantenido su postura.\",\n"
        f"  \"postura_antes\": \"Resumen de lo que decían en {ano_a}\",\n"
        f"  \"postura_despues\": \"Resumen de lo que dicen en {ano_b}\",\n"
        "  \"veredicto_cambio\": \"Elige estrictamente UNA de estas 4 opciones: Giro Radical / Evolución Moderada / Postura Mantenida / Sin Datos\"\n"
        "}\n\n"
        "REGLAS ESTRICTAS:\n"
        "1. Si el tema no aparece en uno de los años, indícalo claramente (ej: 'En 2011 no mencionaban este tema').\n"
        "2. Basa tu análisis ÚNICAMENTE en el contexto proporcionado abajo. No uses conocimiento externo.\n"
        "3. Devuelve ÚNICA y EXCLUSIVAMENTE el JSON en texto plano, sin formato de código markdown."
    )
    
    # Inyectar los dos contextos
    mensajes = [
        ("system", system_prompt),
        ("human", f"--- CONTEXTO AÑO {ano_a} ---\n{contexto_a}\n\n--- CONTEXTO AÑO {ano_b} ---\n{contexto_b}")
    ]
    
    respuesta = llm.invoke(mensajes)
    
    # Limpiar y empaquetar JSON
    contenido = respuesta.content.strip()
    if contenido.startswith("```json"):
        contenido = contenido[7:]
    if contenido.endswith("```"):
        contenido = contenido[:-3]
    contenido = contenido.strip()

    try:
        resultado = json.loads(contenido)
        resultado["ano_a"] = ano_a
        resultado["ano_b"] = ano_b
        resultado["tema"] = tema
        resultado["partido"] = partido
        return resultado
    except json.JSONDecodeError:
        return {
            "error": "La IA ha devuelto un formato incorrecto. Por favor, vuelve a intentarlo."
        }