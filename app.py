import streamlit as st
import os
import re
from langchain_community.document_loaders import PyPDFLoader
from text_cleaner import clean_parliamentary_text
from document_extractor import extract_pnl_by_id, extract_amendment_by_number, extract_full_pdl, extract_speech
from ai_engine import analizar_coherencia, explicar_documento, explorar_programa, comparar_programas
from pdf_generator import generar_pdf
from chart_generator import generar_grafico_donut 

st.set_page_config(page_title="Analizador Parlamentario IA", page_icon="🏛️", layout="wide")

# INICIALIZAR MEMORIA DEL HISTORIAL
if 'historial' not in st.session_state:
    st.session_state['historial'] = []


# FUNCIÓN RASTREADORA DE BASES DE DATOS
def obtener_anos_disponibles(partido):
    anos_totales = ["2011", "2015", "2016", "2019_abr", "2019_nov", "2023"]
    anos_validos = []
    if partido:
        partido_limpio = partido.lower().replace(" ", "_")
        for ano in anos_totales:
            if os.path.exists(f"db_{partido_limpio}_{ano}"):
                anos_validos.append(ano)
    return anos_validos

st.title("Analizador de Iniciativas Parlamentarias y Programas Electorales")

# DESPLEGABLE DE HERRAMIENTAS
st.markdown("### ¿Qué herramienta quieres usar hoy?")
modo_app = st.selectbox(
    "Selecciona la herramienta:",
    (
        "🚦 Modo Auditoría: Analizar coherencia",
        "📖 Modo Explicación: Entender documento",
        "🔎 Modo Búsqueda: Buscar tema en un programa",
        "🕰️ Modo Comparación: Evolución de promesas electorales"
    ),
    label_visibility="collapsed"
)
st.divider()

# DISEÑO EN COLUMNAS
col1, col2 = st.columns(2)

archivo_pdf = None
identificador = ""
tipo_doc = ""
partido_analizar = None
ano_programa = None
postura_partido = None
tema_buscar = ""

if "Auditoría" in modo_app or "Explicación" in modo_app:
    # TRABAJO CON TEXTOS EXTERNOS (es necesario adjuntar PDF)
    with col1:
        tipo_doc = st.selectbox(
            "¿Qué tipo de documento vas a analizar?",
            ("Proyecto / Proposición de Ley (Serie A o B)", "Proposición No de Ley (PNL)", "Enmienda a los PGE", "Diario de Sesiones (Discurso)")
        )

        if "Auditoría" in modo_app:
            partido_analizar = st.selectbox("¿Qué partido político quieres analizar?", ("PP", "PSOE", "SUMAR", "VOX", "ERC", "PODEMOS", "CIUDADANOS"))
            
            anos_disponibles = obtener_anos_disponibles(partido_analizar)
            
            if not anos_disponibles:
                st.error(f"⚠️ Aún no existe ninguna base de datos para {partido_analizar}.")
                ano_programa = None
            else:
                ano_programa = st.selectbox("¿Con qué programa electoral quieres comparar el documento?", anos_disponibles)


            if tipo_doc != "Diario de Sesiones (Discurso)":
                postura_partido = st.radio(
                    "¿Qué votó el partido?",
                    ("A favor / Es el autor", "En contra", "Abstención")
                )

                with st.expander("💡 ¿No sabes qué votó el partido?"):
                    st.markdown("""
                    **Opción 1: Web oficial**
                    1. Busca en la primera página de tu PDF el **número de expediente**.
                    2. Entra en congreso.es > *Iniciativas* > *Búsqueda de iniciativas*.
                    3. Introduce el número y ve a la sección **Votaciones**.
                    
                    **Opción 2: Prensa**
                    
                    Busca en Google el nombre de la iniciativa junto a las palabras *"votación congreso"*.
                    """)
            else:
                postura_partido = "No aplica (Es un discurso)"
        

        if tipo_doc == "Proposición No de Ley (PNL)":
            identificador = st.text_input("Introduce el ID del expediente (ej: 162/001213):")
        elif tipo_doc == "Enmienda a los PGE":
            identificador = st.text_input("Introduce el número de la enmienda (ej: 500):")
        elif tipo_doc == "Diario de Sesiones (Discurso)":
            st.info("💡 Asegúrate de subir un Diario de Sesiones del **Pleno del Congreso**.")
            identificador = st.text_input("Escribe el nombre del orador (ej: CASADO BLANCO:)")

    with col2:
        archivo_pdf = st.file_uploader("Sube el archivo PDF aquí", type="pdf")

else:
    # EXTRAE DE LAS BASES DE DATOS

    todos_partidos = ["PP", "PSOE", "SUMAR", "VOX", "ERC", "PODEMOS", "CIUDADANOS"]
    partidos_validos = []
    
    for p in todos_partidos:
        anos = obtener_anos_disponibles(p)
        if "Búsqueda" in modo_app and len(anos) >= 1:
            partidos_validos.append(p)
        elif "Comparación" in modo_app and len(anos) >= 2:
            partidos_validos.append(p)


    with col1:
        if not partidos_validos:
            st.error("⚠️ No hay suficientes bases de datos creadas para usar esta función.")
            partido_buscar = None
        else:
            partido_buscar = st.selectbox("¿Qué partido quieres explorar?", partidos_validos)
            tema_buscar = st.text_input("Escribe el tema a buscar (ej: Vivienda, Impuestos, Sanidad, Ley de Costas):")
        
    with col2:
        if partido_buscar:
            anos_disponibles = obtener_anos_disponibles(partido_buscar)
        
            if "Búsqueda" in modo_app:
                ano_buscar = st.selectbox("¿De qué año quieres leer el programa?", anos_disponibles)
            else:                
                ano_a = st.selectbox("Año inicial:", anos_disponibles[:-1])
                
                if ano_a:
                    indice_a = anos_disponibles.index(ano_a)
                    anos_posteriores = anos_disponibles[indice_a + 1:]
                    ano_b = st.selectbox("Año final:", list(reversed(anos_posteriores)))


# PROCESAMIENTO
st.divider()

if "Auditoría" in modo_app or "Explicación" in modo_app:
    if archivo_pdf is not None:
        if st.button("Procesar Documento", type="primary"):
            with st.spinner("Leyendo y extrayendo el documento..."):
                with open("temp.pdf", "wb") as f:
                    f.write(archivo_pdf.getvalue())
                
                loader = PyPDFLoader("temp.pdf")
                paginas = loader.load()
                texto_completo = "".join([clean_parliamentary_text(p.page_content) + " " for p in paginas])
                
                if tipo_doc == "Proyecto / Proposición de Ley (Serie A o B)":
                    texto_final = extract_full_pdl(texto_completo)
                elif tipo_doc == "Proposición No de Ley (PNL)":
                    texto_final = extract_pnl_by_id(texto_completo, id_expediente=identificador)
                elif tipo_doc == "Enmienda a los PGE":
                    texto_final = extract_amendment_by_number(texto_completo, num_enmienda=identificador)
                elif tipo_doc == "Diario de Sesiones (Discurso)":
                    texto_final = extract_speech(texto_completo, orador=identificador)
                else:
                    texto_final = ""
                
                if os.path.exists("temp.pdf"):
                    os.remove("temp.pdf")
                    
            if texto_final:
                if "Auditoría" in modo_app:
                    with st.spinner("Analizando coherencia con IA..."):
                        analisis_bruto = analizar_coherencia(texto_final, partido_analizar, ano_programa, postura_partido)
                        
                        match = re.search(r'\[PORCENTAJE:\s*(\d+)\]', analisis_bruto)
                        if match:
                            porcentaje = int(match.group(1))
                            texto_limpio = re.sub(r'(?i)(4\.\s*PORCENTAJE.*|\[PORCENTAJE:.*\])', '', analisis_bruto, flags=re.DOTALL).strip()
                        else:
                            porcentaje = 0
                            texto_limpio = analisis_bruto

                        st.session_state['analisis_completado'] = True
                        st.session_state['modo_usado'] = "Auditoria"
                        st.session_state['porcentaje'] = porcentaje
                        st.session_state['texto_limpio'] = texto_limpio
                        st.session_state['partido'] = partido_analizar
                        st.session_state['ano'] = ano_programa

                        st.session_state['historial'].insert(0, {
                            "modo": "Auditoria",
                            "partido": partido_analizar,
                            "ano": ano_programa,
                            "porcentaje": porcentaje,
                            "texto": texto_limpio
                        })
                else:
                    with st.spinner("Traduciendo el documento..."):
                        resultado_json = explicar_documento(texto_final)
                        
                        st.session_state['analisis_completado'] = True
                        st.session_state['modo_usado'] = "Explicacion"
                        st.session_state['resultado_explicacion'] = resultado_json
                        st.session_state['tipo_doc_explicacion'] = tipo_doc

                        st.session_state['historial'].insert(0, {
                            "modo": "Explicacion",
                            "tipo_doc": tipo_doc,
                            "resultado": resultado_json
                        })
            else:
                st.error("**Alerta de Incompatibilidad**")
                st.warning(f"No he podido encontrar el formato para **{tipo_doc}**.")
else:
    # BUSQUEDA EN BASES DE DATOS
    if tema_buscar:
        if st.button("Buscar", type="primary"):
            with st.spinner("Buscando en los programas electorales..."):
                
                if "Búsqueda" in modo_app:
                    resultado_json = explorar_programa(partido_buscar, ano_buscar, tema_buscar)
                    modo_guardar = "Busqueda"
                else:
                    resultado_json = comparar_programas(partido_buscar, ano_a, ano_b, tema_buscar)
                    modo_guardar = "Comparacion"

                st.session_state['analisis_completado'] = True
                st.session_state['modo_usado'] = modo_guardar
                st.session_state['resultado_hemeroteca'] = resultado_json
                st.session_state['partido_hemeroteca'] = partido_buscar
                st.session_state['tema_hemeroteca'] = tema_buscar

                st.session_state['historial'].insert(0, {
                    "modo": modo_guardar,
                    "partido": partido_buscar,
                    "tema": tema_buscar,
                    "resultado": resultado_json
                })


# RESULTADOS
if st.session_state.get('analisis_completado', False):
    
    if st.session_state.get('modo_usado') == "Auditoria":
        porcentaje = st.session_state['porcentaje']
        texto_limpio = st.session_state['texto_limpio']
        partido = st.session_state['partido']
        ano = st.session_state['ano']

        fig, mensaje = generar_grafico_donut(porcentaje)
        st.success("Análisis de coherencia completado")
        
        col_grafico, col_texto = st.columns([1, 2])
        with col_grafico:
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f"<h4 style='text-align: center;'>{mensaje}</h4>", unsafe_allow_html=True)
        with col_texto:
            st.write("### Veredicto de la IA")
            st.write(texto_limpio)
        st.markdown("---")
        
        pdf_bytes = generar_pdf(partido, ano, porcentaje, texto_limpio)
        st.download_button("Descargar Análisis en PDF", data=pdf_bytes, file_name=f"Analisis_{partido}_{ano}.pdf", mime="application/pdf")
    
    elif st.session_state.get('modo_usado') == "Explicacion":
        resultado = st.session_state['resultado_explicacion']
        if "error" in resultado:
            st.error("⚠️ Hubo un problema al traducir el documento.")
            st.write(resultado["error"])
        else:
            st.success("Explicación completada")
            st.markdown("### En pocas palabras")
            st.info(resultado.get('idea_principal', 'Resumen no disponible'))
            st.markdown("### ¿A quién afecta y cómo?")
            st.info(resultado.get('impacto', 'Impacto no disponible'))
            st.markdown("### Diccionario")
            diccionario = resultado.get('diccionario', {})
            if diccionario:
                for termino, explicacion in diccionario.items():
                    with st.expander(f"¿Qué significa **{termino}**?"):
                        st.write(explicacion)
            else:
                st.write("Este texto no tenía demasiados conceptos complicados.")
            st.markdown("---")

    # RESULTADOS DE LA BÚSQUEDA EN PE
    elif st.session_state.get('modo_usado') == "Busqueda":
        resultado = st.session_state['resultado_hemeroteca']
        partido = st.session_state['partido_hemeroteca']
        tema = st.session_state['tema_hemeroteca']

        if "error" in resultado:
            st.error(resultado["error"])
        else:
            st.success(f"Exploración completada: {partido.upper()} sobre '{tema}'")
            
            st.markdown("### Postura General")
            st.write(resultado.get('postura_general', 'No disponible'))
            
            st.markdown("### Medidas Clave")
            medidas = resultado.get('medidas_clave', [])
            if medidas:
                for medida in medidas:
                    st.markdown(f"- {medida}")
            else:
                st.write("No se han encontrado medidas concretas sobre este tema.")
                
            st.markdown("### Cita Literal")
            cita = resultado.get('cita_destacada', 'No hay citas')
            pagina = resultado.get('pagina_cita', 'Desconocida')
            
            st.info(f"« *{cita}* »")
            st.caption(f"**Fuente:** Extraído de la página {pagina} del programa electoral.")
            st.markdown("---")

    # RESULTADOS DE LA COMPARACIÓN 
    elif st.session_state.get('modo_usado') == "Comparacion":
        resultado = st.session_state['resultado_hemeroteca']
        partido = st.session_state['partido_hemeroteca']
        tema = st.session_state['tema_hemeroteca']

        if "error" in resultado:
            st.error(resultado["error"])
        else:
            st.success(f"Comparativa completada: {partido.upper()} sobre '{tema}'")
            
            veredicto = resultado.get('veredicto_cambio', '')
            if "Radical" in veredicto:
                st.error(f"**Veredicto de la IA:** {veredicto}")
            elif "Moderada" in veredicto:
                st.warning(f"**Veredicto de la IA:** {veredicto}")
            elif "Mantenida" in veredicto:
                st.success(f"**Veredicto de la IA:** {veredicto}")
            else:
                st.info(f"**Veredicto de la IA:** {veredicto}")

            st.markdown("### Resumen de la Evolución")
            st.write(resultado.get('resumen_evolucion', 'No disponible'))
            
            col_antes, col_despues = st.columns(2)
            with col_antes:
                st.markdown(f"#### Antes ({resultado.get('ano_a', 'Año A')})")
                st.info(resultado.get('postura_antes', 'No disponible'))
            with col_despues:
                st.markdown(f"#### Después ({resultado.get('ano_b', 'Año B')})")
                st.info(resultado.get('postura_despues', 'No disponible'))
            
            st.markdown("---")


# HISTORIAL DE SESIÓN
with st.sidebar:
    st.header("Historial de Sesión")
    st.write("Aquí se guardan tus análisis mientras no cierres la pestaña.")
    st.divider()

    if len(st.session_state['historial']) == 0:
        st.info("Aún no has analizado ningún documento.")
    else:
        for i, item in enumerate(st.session_state['historial']):
            if item.get("modo") in ["Auditoria", "Auditoría", "Experto"]:
                if item['porcentaje'] < 50:
                    icono = "🔴"
                elif item['porcentaje'] < 85:
                    icono = "🟠"
                else:
                    icono = "🟢"
                with st.expander(f"{icono} Análisis {item['partido'].upper()} ({item['ano']}) - {item['porcentaje']}%"):
                    st.write(item['texto'])

            elif item.get("modo") == "Explicacion":
                nombre_doc = item.get('tipo_doc', 'Documento')
                with st.expander(f"📖 Explicación {nombre_doc[:30]}"):
                    if "error" not in item.get('resultado', {}):
                        st.write(f"**Idea:** {item['resultado'].get('idea_principal', 'No disponible')}")
                    else:
                        st.write("Análisis fallido.")

            elif item.get("modo") == "Busqueda":
                with st.expander(f"🔎 Búsqueda {item['partido'].upper()} - {item['tema']}"):
                    if "error" not in item.get('resultado', {}):
                        postura = item['resultado'].get('postura_general', '')
                        st.write(f"{postura[:100]}..." if len(postura) > 100 else postura)
                    else:
                        st.write("Búsqueda fallida.")

            elif item.get("modo") == "Comparacion":
                with st.expander(f"🕰️ Comparación {item['partido'].upper()} - {item['tema']}"):
                    if "error" not in item.get('resultado', {}):
                        st.write(f"**Evolución:** {item['resultado'].get('veredicto_cambio', '')}")
                    else:
                        st.write("Búsqueda fallida.")
