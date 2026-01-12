import streamlit as st
import google.generativeai as genai
import json
import io
from docx import Document
# Importamos el prompt (asegúrate de que organon_prompts.py sigue en la misma carpeta)
from organon_prompts import SYSTEM_PROMPT_ZH as SYSTEM_PROMPT 

# --- 1. CONFIGURACIÓN DE PÁGINA (PAGE CONFIG) ---
st.set_page_config(
    page_title="Organon Iudiciale | 法律書狀生成系統",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. INYECCIÓN DE ESTILO (CSS - GRAVITAS THEME 2026) ---
st.markdown("""
    <style>
    /* Fondo General - Limpio y Profesional */
    .stApp {
        background-color: #F8F9FA;
    }
    /* Títulos Principales (H1, H2, H3) - Azul Marino Institucional */
    h1, h2, h3 {
        color: #1C2E4A !important;
        font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif;
        font-weight: 600;
    }
    /* Botones Normales */
    .stButton>button {
        color: #1C2E4A;
        border: 1px solid #1C2E4A;
        border-radius: 4px;
        background-color: white;
    }
    /* Botón Primario (Generar) - Destacado */
    div.stButton > button:first-child {
        background-color: #1C2E4A;
        color: white;
        border: none;
        font-weight: bold;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    div.stButton > button:hover {
        background-color: #2c456b; /* Un poco más claro al pasar el mouse */
        color: white;
    }
    /* Inputs y Text Areas - Fondo blanco puro con borde suave */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #FFFFFF;
        border: 1px solid #CED4DA;
        color: #212529;
    }
    /* Sidebar - Gris muy suave para contraste */
    section[data-testid="stSidebar"] {
        background-color: #E9ECEF;
    }
    /* Expander Headers */
    .streamlit-expanderHeader {
        color: #1C2E4A;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONFIGURACIÓN GEMINI (MODELO 2026) ---
# ACTUALIZACIÓN 2026: Implementación de la serie Gemini 3.0 Flash
MODEL_NAME = "gemini-3.0-flash" 

try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ 嚴重錯誤：未檢測到 GOOGLE_API_KEY。請檢查 Secrets 設定 (Severe Error: API Key missing).")
    st.stop()

# --- ESTADO DE SESIÓN ---
if 'api_calls' not in st.session_state:
    st.session_state.api_calls = 0
MAX_CALLS = 10

# --- FUNCIÓN WORD (EXPORT) ---
def crear_documento_word(titulo, cuerpo, analisis, receptor):
    doc = Document()
    
    # Intentamos configurar la fuente predeterminada
    style = doc.styles['Normal']
    font = style.font
    font.name = 'PMingLiU' # Nueva MingLiu (Estándar en documentos legales de Taiwán)
    
    # Encabezado del documento
    doc.add_paragraph(f"致 (To): {receptor}", style='Heading 2')
    doc.add_heading(titulo, 0)
    
    # Cuerpo Principal
    doc.add_heading('書狀內容 (Content):', level=1)
    doc.add_paragraph(cuerpo)
    
    # Anexo Estratégico (Inventio)
    doc.add_page_break()
    doc.add_heading('附件：AI 策略分析 (Inventio Analysis)', level=1)
    doc.add_paragraph(f"爭點狀態 (Status Causae): {analisis.get('status_causae', 'N/A')}")
    doc.add_paragraph(f"防禦策略 (Defense Strategy): {analisis.get('estrategia_defensa', 'N/A')}")
    doc.add_paragraph(f"核心法律依據 (Key Legal Basis): {analisis.get('puntos_clave', 'N/A')}")
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- FUNCIÓN LLAMADA API ---
def generar_escrito(datos):
    if st.session_state.api_calls >= MAX_CALLS:
        return {"error": "已達到試用版次數限制 (10/10)。請聯繫管理員升級。(Demo limit reached)"}
    
    # Configuración optimizada para Gemini 3.0 Flash
    generation_config = {
        "temperature": 0.3, # Gemini 3 tiene mejor razonamiento, bajamos temperatura para máxima precisión legal
        "top_p": 0.95,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
        generation_config=generation_config,
    )

    # Prompt del Usuario (User Prompt)
    user_prompt = f"""
    請根據以下資訊撰寫法律書狀 (Draft request):

    --- 基本設定 (Settings) ---
    【致送機關 (Recipient)】: {datos['receptor']}
    【語氣風格 (Tone/Style)】: {datos['tono']} 
    (Instruction: Strictly adapt the writing style to this tone. e.g., if 'Conservative', use humble/archaic terms; if 'Aggressive', use sharp logic.)

    --- 案件內容 (Case Details) ---
    1. 【案情事實 (Hechos)】: 
    {datos['hechos']}
    
    2. 【引用法條 (Leyes)】: 
    {datos['leyes'] if datos['leyes'] else "由系統自行判斷適用法條 (System discretion)"}

    3. 【引用實務見解 (Jurisprudencia)】: 
    {datos['jurisprudencia'] if datos['jurisprudencia'] else "無特定引用 (None)"}

    4. 【關鍵證據 (Pruebas)】: 
    {datos['pruebas']}
    
    5. 【對造主張 (Contraparte)】: 
    {datos['contraparte']}
    
    6. 【訴之聲明/目標 (Objetivo)】: 
    {datos['objetivo']}
    """

    try:
        response = model.generate_content(user_prompt)
        st.session_state.api_calls += 1
        return json.loads(response.text)
    except Exception as e:
        # Fallback de seguridad por si el endpoint 3.0 tiene latencia
        return {"error": f"Gemini 3.0 系統發生錯誤: {str(e)}"}

# --- INTERFAZ DE USUARIO (FRONTEND) ---

# Header Institucional
st.markdown("""
    <div style='text-align: center; padding-bottom: 20px;'>
        <h1 style='color: #1C2E4A; margin-bottom: 0;'>⚖️ Organon Iudiciale</h1>
        <p style='color: #666; font-size: 1.1em;'>台灣法律書狀 AI 生成系統 (專業版)</p>
        <div style='height: 2px; background-color: #1C2E4A; width: 100px; margin: 10px auto;'></div>
    </div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 📝 案件資訊輸入 (Input Case Data)")
    st.info("💡 提示：輸入越精確的「法條」與「判決字號」，生成的書狀將越具說服力。")
    
    with st.form("main_form"):
        # SECCIÓN 0: Contexto
        st.markdown("**0. 致送對象與風格 (Context & Tone)**")
        c1, c2 = st.columns(2)
        with c1:
            receptor = st.text_input("受文者 (Recipient)", placeholder="例如：臺灣臺北地方法院民事庭")
        with c2:
            tono = st.text_input("書寫語氣 (Tone)", placeholder="例如：莊重保守、犀利、懇切...")

        # SECCIÓN 1: Hechos
        st.markdown("**1. 基礎事實與目標 (Facts & Goal)**")
        hechos = st.text_area("案情事實 (Facts)", height=100, placeholder="請依時間序列描述發生經過...")
        objetivo = st.text_input("訴之聲明 / 目標 (Objective)", placeholder="例如：請求駁回原告之訴...")

        # SECCIÓN 2: Leyes
        st.markdown("**2. 法源依據 (Legal Basis)**")
        leyes = st.text_area("引用法條 (Laws)", height=70, placeholder="例如：民法第184條...")
        with st.expander("進階：引用實務見解 (Jurisprudence)"):
            jurisprudencia = st.text_area("相關判決字號", height=70, placeholder="例如：最高法院 100 年度台上字第 1234 號")

        # SECCIÓN 3: Estrategia
        st.markdown("**3. 攻防細節 (Strategy Details)**")
        pruebas = st.text_area("關鍵證據 (Evidence)", height=70, placeholder="證物、對話紀錄...")
        contraparte = st.text_area("對造主張 (Counter-argument)", height=70, placeholder="對方如何主張？")
        
        submitted = st.form_submit_button("🚀 生成法律書狀 (Generate Document)")

with col2:
    st.markdown("### 📄 書狀預覽 (Document Preview)")
    
    if submitted:
        if not hechos or not objetivo or not receptor:
            st.warning("⚠️ 請填寫必要欄位：【受文者】、【案情事實】與【訴之聲明】。")
        else:
            with st.spinner(f"⚖️ Organon 正在思考中... (Engine: {MODEL_NAME})"):
                # Tone default logic
                tono_final = tono if tono else "專業、莊重 (Professional/Solemn)"
                
                datos = {
                    "receptor": receptor, "tono": tono_final,
                    "hechos": hechos, "leyes": leyes, "jurisprudencia": jurisprudencia,
                    "pruebas": pruebas, "contraparte": contraparte, "objetivo": objetivo
                }
                resultado = generar_escrito(datos)
            
            if "error" in resultado:
                st.error(f"❌ {resultado['error']}")
            else:
                doc_final = resultado.get("documento_final", {})
                analisis = resultado.get("analisis_estrategico", {})
                
                # Visualización Estrategia (Inventio)
                with st.expander("🧠 AI 策略分析 (Inventio Strategy)", expanded=True):
                    st.markdown(f"**核心爭點 (Status):** {analisis.get('status_causae')}")
                    st.markdown(f"**防禦策略 (Strategy):** {analisis.get('estrategia_defensa')}")
                    if analisis.get('puntos_clave'):
                        st.markdown(f"**關鍵法源:** {analisis.get('puntos_clave')}")

                # Visualización Documento (Dictio)
                titulo = doc_final.get('titulo', '法律書狀')
                texto = doc_final.get('texto_completo', '')
                
                st.markdown(f"#### {titulo}")
                st.markdown(f"**致：{receptor}**") 
                st.code(texto, language=None)
                
                # Botón Descarga Word
                st.markdown("---")
                docx = crear_documento_word(titulo, texto, analisis, receptor)
                st.download_button(
                    label="💾 下載 Word 檔 (.docx)",
                    data=docx,
                    file_name=f"{titulo}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary"
                )

# Footer
st.divider()
st.caption(f"系統狀態：Online | Model: {MODEL_NAME} | Date: 2026.01.13")
