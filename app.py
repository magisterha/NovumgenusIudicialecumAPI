import streamlit as st
import google.generativeai as genai # Librería oficial de Google
import json
import io
from docx import Document
# Importamos el prompt (asegúrate de que organon_prompts.py sigue ahí)
from organon_prompts import SYSTEM_PROMPT_ZH as SYSTEM_PROMPT 

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Organon Iudiciale (Gemini Powered)",
    page_icon="⚖️",
    layout="wide"
)

# --- CONFIGURACIÓN DE GEMINI ---
# Nombre del modelo (Verifica el nombre exacto en AI Studio, a veces cambia la fecha)
MODEL_NAME = "gemini-2.0-flash-lite-preview-02-05" 

try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ Error: No se encontró la GOOGLE_API_KEY en los secretos.")
    st.stop()

# --- ESTADO DE SESIÓN ---
if 'api_calls' not in st.session_state:
    st.session_state.api_calls = 0
MAX_CALLS = 10

# --- FUNCIÓN: GENERAR WORD ---
def crear_documento_word(titulo, cuerpo, analisis):
    doc = Document()
    doc.add_heading(titulo, 0)
    doc.add_heading('Escrito Judicial (本文):', level=1)
    doc.add_paragraph(cuerpo)
    doc.add_page_break()
    doc.add_heading('Anexo: Estrategia IA', level=1)
    doc.add_paragraph(f"Status: {analisis.get('status_causae', 'N/A')}")
    doc.add_paragraph(f"Estrategia: {analisis.get('estrategia_defensa', 'N/A')}")
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- FUNCIÓN: LLAMADA API (GEMINI 2.0) ---
def generar_escrito(datos):
    if st.session_state.api_calls >= MAX_CALLS:
        return {"error": "Límite de demo alcanzado."}
    
    # 1. Configuración de Generación (Forzamos JSON)
    generation_config = {
        "temperature": 0.5,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json", # ¡Clave para Gemini!
    }

    # 2. Inicializamos el modelo con el System Prompt inyectado
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT, # Inyección nativa
        generation_config=generation_config,
    )

    # 3. Construimos el Prompt de Usuario
    user_prompt = f"""
    請根據以下資訊撰寫法律書狀 (Draft request):

    1. 【案情事實 (Hechos)】: 
    {datos['hechos']}
    
    2. 【引用法條 (Leyes - Strict adherence)】: 
    {datos['leyes'] if datos['leyes'] else "由系統自行判斷"}

    3. 【引用判決 (Jurisprudencia)】: 
    {datos['jurisprudencia'] if datos['jurisprudencia'] else "無"}

    4. 【證據 (Pruebas)】: 
    {datos['pruebas']}
    
    5. 【對造主張 (Contraparte)】: 
    {datos['contraparte']}
    
    6. 【訴訟目標 (Objetivo)】: 
    {datos['objetivo']}
    """

    try:
        # Llamada a Gemini
        response = model.generate_content(user_prompt)
        
        # Incremento contador
        st.session_state.api_calls += 1
        
        # Parseo de respuesta
        # Gemini con response_mime_type ya devuelve un string JSON limpio
        return json.loads(response.text)

    except Exception as e:
        return {"error": f"Error de Gemini: {str(e)}"}

# --- INTERFAZ (FRONTEND) ---
# (Esta parte es idéntica a la anterior, solo cambia el motor por debajo)
st.title("⚖️ Organon Iudiciale")
st.caption(f"Powered by Google {MODEL_NAME}") # Indicador visual del modelo

col1, col2 = st.columns([1, 1])

with col1:
    st.info("💡 Consejo: Introduce las leyes exactas para evitar errores.")
    with st.form("main_form"):
        hechos = st.text_area("1. Hechos del Caso (事實)", height=120)
        st.markdown("**🛡️ Fundamentación Legal**")
        leyes = st.text_area("2. Leyes Aplicables (引用法條)", height=80)
        with st.expander("3. Jurisprudencia / Sentencias (Opcional)"):
            jurisprudencia = st.text_area("Sentencias Relacionadas (引用判決)", height=80)
        st.markdown("---")
        pruebas = st.text_area("4. Pruebas Clave (證據)", height=80)
        contraparte = st.text_area("5. Argumento Contrario (對造主張)", height=80)
        objetivo = st.text_input("6. Objetivo Legal (訴訟目標)")
        
        submitted = st.form_submit_button("🚀 Generar Escrito (Gemini)")

with col2:
    if submitted:
        if not hechos or not objetivo:
            st.warning("⚠️ Faltan datos esenciales.")
        else:
            with st.spinner("⚖️ Gemini está analizando leyes y redactando..."):
                datos = {
                    "hechos": hechos, "leyes": leyes, "jurisprudencia": jurisprudencia,
                    "pruebas": pruebas, "contraparte": contraparte, "objetivo": objetivo
                }
                resultado = generar_escrito(datos)
            
            if "error" in resultado:
                st.error(resultado["error"])
            else:
                doc_final = resultado.get("documento_final", {})
                analisis = resultado.get("analisis_estrategico", {})
                
                with st.expander("🧠 Ver Estrategia Legal", expanded=True):
                    st.write(f"**Estrategia:** {analisis.get('estrategia_defensa')}")
                    st.caption("Verifica que las leyes citadas sean correctas.")

                titulo = doc_final.get('titulo', 'Documento Legal')
                texto = doc_final.get('texto_completo', '')
                
                st.markdown(f"### {titulo}")
                st.code(texto, language=None)
                
                docx = crear_documento_word(titulo, texto, analisis)
                st.download_button("💾 Descargar Word", docx, "escrito_legal.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

st.divider()
st.caption(f"Demo Version | Calls: {st.session_state.api_calls}/{MAX_CALLS}")
