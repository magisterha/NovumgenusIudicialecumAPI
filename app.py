import streamlit as st
import google.generativeai as genai
import json
import io
from docx import Document
# Importamos el prompt (asegúrate de que organon_prompts.py sigue ahí)
from organon_prompts import SYSTEM_PROMPT_ZH as SYSTEM_PROMPT 

# --- CONFIGURACIÓN DE PÁGINA (必須是第一行) ---
st.set_page_config(
    page_title="Organon Iudiciale | 法律書狀生成系統",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURACIÓN DE GEMINI ---
# Nombre del modelo (Verifica en AI Studio si cambia)
MODEL_NAME = "gemini-2.0-flash-lite-preview-02-05" 

try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ 錯誤：未檢測到 GOOGLE_API_KEY。請檢查 Secrets 設定。")
    st.stop()

# --- ESTADO DE SESIÓN ---
if 'api_calls' not in st.session_state:
    st.session_state.api_calls = 0
MAX_CALLS = 10

# --- FUNCIÓN: GENERAR WORD ---
def crear_documento_word(titulo, cuerpo, analisis):
    doc = Document()
    # Estilo básico
    style = doc.styles['Normal']
    font = style.font
    font.name = 'PMingLiU' # Intentamos usar tipografía taiwanesa estándar (MingLiU) si está disponible

    doc.add_heading(titulo, 0)
    doc.add_heading('書狀內容 (本文):', level=1)
    doc.add_paragraph(cuerpo)
    
    doc.add_page_break()
    doc.add_heading('附件：AI 策略分析 (Inventio)', level=1)
    doc.add_paragraph(f"爭點狀態 (Status): {analisis.get('status_causae', 'N/A')}")
    doc.add_paragraph(f"防禦策略 (Estrategia): {analisis.get('estrategia_defensa', 'N/A')}")
    doc.add_paragraph(f"法律依據 (Puntos Clave): {analisis.get('puntos_clave', 'N/A')}")
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- FUNCIÓN: LLAMADA API (GEMINI 2.0) ---
def generar_escrito(datos):
    if st.session_state.api_calls >= MAX_CALLS:
        return {"error": "已達到試用版次數限制 (10/10)。"}
    
    # 1. Configuración de Generación
    generation_config = {
        "temperature": 0.5, # Precisión jurídica
        "top_p": 0.95,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }

    # 2. Inicializar Modelo
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
        generation_config=generation_config,
    )

    # 3. Prompt del Usuario (Interno)
    user_prompt = f"""
    請根據以下資訊撰寫法律書狀 (Draft request):

    1. 【案情事實 (Hechos)】: 
    {datos['hechos']}
    
    2. 【引用法條 (Leyes)】: 
    {datos['leyes'] if datos['leyes'] else "由系統自行判斷適用法條"}

    3. 【引用實務見解 (Jurisprudencia)】: 
    {datos['jurisprudencia'] if datos['jurisprudencia'] else "無特定引用"}

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
        return {"error": f"系統發生錯誤 (Gemini Error): {str(e)}"}

# --- INTERFAZ (FRONTEND - TRADITIONAL CHINESE) ---

# Header con estilo profesional
st.markdown("""
    <h1 style='text-align: center; color: #1C2E4A;'>⚖️ Organon Iudiciale</h1>
    <p style='text-align: center; color: #666;'>台灣法律書狀 AI 生成系統 (專業版)</p>
    <hr>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 📝 案件資訊輸入 (Input)")
    st.info("💡 提示：輸入越精確的「法條」與「判決字號」，生成的書狀將越具說服力。")
    
    with st.form("main_form"):
        st.markdown("**1. 基礎事實與目標**")
        hechos = st.text_area("案情事實 (Facts)", height=120, placeholder="請依時間序列描述發生經過...")
        objetivo = st.text_input("訴之聲明 / 訴訟目標 (Objective)", placeholder="例如：請求駁回原告之訴、請求損害賠償...")

        st.markdown("---")
        st.markdown("**2. 法源依據 (Legal Basis)**")
        leyes = st.text_area("引用法條 (Applicable Laws)", height=80, placeholder="例如：民法第184條第1項前段、刑法第339條...")
        
        with st.expander("進階：引用實務見解 / 判決 (Jurisprudence)"):
            jurisprudencia = st.text_area("相關判決字號", height=80, placeholder="例如：最高法院 100 年度台上字第 1234 號...")

        st.markdown("---")
        st.markdown("**3. 攻防策略 (Strategy)**")
        pruebas = st.text_area("關鍵證據 (Evidence)", height=80, placeholder="例如：LINE對話紀錄、匯款單、證人證詞...")
        contraparte = st.text_area("對造主張 (Counter-argument)", height=80, placeholder="對方是如何主張的？我方需要反駁什麼？")
        
        submitted = st.form_submit_button("🚀 生成法律書狀 (Generate)")

with col2:
    st.markdown("### 📄 書狀預覽 (Preview)")
    
    if submitted:
        if not hechos or not objetivo:
            st.warning("⚠️ 請填寫必要欄位：【案情事實】與【訴之聲明】。")
        else:
            # Barra de progreso visual
            with st.spinner("⚖️ 正在分析案情並撰寫書狀中 (Inventio ➤ Dispositio ➤ Dictio)..."):
                datos = {
                    "hechos": hechos, "leyes": leyes, "jurisprudencia": jurisprudencia,
                    "pruebas": pruebas, "contraparte": contraparte, "objetivo": objetivo
                }
                resultado = generar_escrito(datos)
            
            if "error" in resultado:
                st.error(f"❌ {resultado['error']}")
            else:
                doc_final = resultado.get("documento_final", {})
                analisis = resultado.get("analisis_estrategico", {})
                
                # Visualización de Estrategia
                with st.expander("🧠 AI 策略分析 (Inventio Strategy)", expanded=True):
                    st.markdown(f"**核心爭點 (Status):** {analisis.get('status_causae')}")
                    st.markdown(f"**防禦策略:** {analisis.get('estrategia_defensa')}")
                    st.caption("請律師複查引用法條之正確性 (Grounding Check)。")

                # Visualización del Documento
                titulo = doc_final.get('titulo', '法律書狀')
                texto = doc_final.get('texto_completo', '')
                
                st.markdown(f"#### {titulo}")
                st.code(texto, language=None)
                
                # Botón de Descarga
                st.markdown("---")
                docx = crear_documento_word(titulo, texto, analisis)
                st.download_button(
                    label="💾 下載 Word 檔 (.docx)",
                    data=docx,
                    file_name=f"{titulo}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary" # Hace el botón más destacado
                )

# Footer
st.divider()
st.caption(f"系統狀態：線上 | 剩餘試用次數：{MAX_CALLS - st.session_state.api_calls}/{MAX_CALLS} | 模型：Google {MODEL_NAME}")
