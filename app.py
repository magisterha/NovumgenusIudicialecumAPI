import streamlit as st
import google.generativeai as genai
import json
import io
from docx import Document
# Importamos el prompt (asegúrate de que organon_prompts.py sigue en la misma carpeta)
from organon_prompts import SYSTEM_PROMPT_ZH as SYSTEM_PROMPT 

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Organon Iudiciale | 法律書狀生成系統",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. INYECCIÓN DE ESTILO (CSS DIRECTO) ---
# Esto define los colores "Serios" sin usar config.toml
st.markdown("""
    <style>
    /* Fondo General */
    .stApp {
        background-color: #Fdfdfd;
    }
    /* Títulos Principales (H1, H2, H3) - Azul Marino Institucional */
    h1, h2, h3 {
        color: #1C2E4A !important;
        font-family: 'Microsoft JhengHei', sans-serif;
    }
    /* Botones Normales */
    .stButton>button {
        color: #1C2E4A;
        border: 1px solid #1C2E4A;
        border-radius: 4px;
    }
    /* Botón Primario (Generar) */
    div.stButton > button:first-child {
        background-color: #1C2E4A;
        color: white;
        border: none;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #2c456b;
        color: white;
    }
    /* Inputs y Text Areas */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #FAFAFA;
        border: 1px solid #E0E0E0;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #F0F2F6;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONFIGURACIÓN GEMINI ---
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

# --- FUNCIÓN WORD ---
def crear_documento_word(titulo, cuerpo, analisis, receptor):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'PMingLiU' # Intentamos usar tipografía MingLiU (Estándar Taiwán)

    # Añadimos el Receptor al principio del Word
    doc.add_paragraph(f"致：{receptor}", style='Heading 2')
    
    doc.add_heading(titulo, 0)
    doc.add_paragraph(cuerpo)
    
    doc.add_page_break()
    doc.add_heading('附件：AI 策略分析 (Inventio)', level=1)
    doc.add_paragraph(f"爭點狀態 (Status): {analisis.get('status_causae', 'N/A')}")
    doc.add_paragraph(f"防禦策略 (Estrategia): {analisis.get('estrategia_defensa', 'N/A')}")
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- FUNCIÓN LLAMADA API ---
def generar_escrito(datos):
    if st.session_state.api_calls >= MAX_CALLS:
        return {"error": "已達到試用版次數限制 (10/10)。"}
    
    generation_config = {
        "temperature": 0.5,
        "top_p": 0.95,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
        generation_config=generation_config,
    )

    # PROMPT DE USUARIO ACTUALIZADO CON RECEPTOR Y TONO
    user_prompt = f"""
    請根據以下資訊撰寫法律書狀 (Draft request):

    --- 基本設定 ---
    【致送機關 (Recipient)】: {datos['receptor']}
    【語氣風格 (Tone/Style)】: {datos['tono']} (請務必依照此語氣調整用詞，例如：若為保守法官請極度謙抑；若為攻擊請犀利)

    --- 案件內容 ---
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

# --- INTERFAZ DE USUARIO (FRONTEND) ---

st.markdown("""
    <h1 style='text-align: center;'>⚖️ Organon Iudiciale</h1>
    <p style='text-align: center; color: #555;'>台灣法律書狀 AI 生成系統 (專業版)</p>
    <hr style='border: 1px solid #1C2E4A;'>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 📝 案件資訊輸入 (Input)")
    
    with st.form("main_form"):
        # SECCIÓN 0: Contexto Institucional (NUEVO)
        st.markdown("**0. 致送對象與風格 (Context)**")
        c1, c2 = st.columns(2)
        with c1:
            receptor = st.text_input("受文者 (Recipient)", placeholder="例如：臺灣臺北地方法院民事庭、檢察署...")
        with c2:
            tono = st.text_input("書寫語氣 (Tone)", placeholder="例如：莊重保守(適合資深法官)、犀利攻擊、懇切求情...")

        # SECCIÓN 1: Hechos
        st.markdown("**1. 基礎事實與目標 (Facts)**")
        hechos = st.text_area("案情事實", height=100, placeholder="請依時間序列描述發生經過...")
        objetivo = st.text_input("訴之聲明 / 目標", placeholder="例如：請求駁回原告之訴...")

        # SECCIÓN 2: Leyes
        st.markdown("**2. 法源依據 (Legal Basis)**")
        leyes = st.text_area("引用法條", height=70, placeholder="例如：民法第184條...")
        with st.expander("進階：引用實務見解 (Jurisprudence)"):
            jurisprudencia = st.text_area("相關判決字號", height=70)

        # SECCIÓN 3: Estrategia
        st.markdown("**3. 攻防細節 (Details)**")
        pruebas = st.text_area("關鍵證據", height=70, placeholder="證物、對話紀錄...")
        contraparte = st.text_area("對造主張", height=70, placeholder="對方如何攻擊？")
        
        submitted = st.form_submit_button("🚀 生成法律書狀 (Generate)")

with col2:
    st.markdown("### 📄 書狀預覽 (Preview)")
    
    if submitted:
        if not hechos or not objetivo or not receptor:
            st.warning("⚠️ 請填寫【受文者】、【案情事實】與【訴之聲明】。")
        else:
            with st.spinner("⚖️ 正在分析案情並撰寫書狀中 (Inventio ➤ Dispositio ➤ Dictio)..."):
                # Si el usuario no pone tono, ponemos uno por defecto
                tono_final = tono if tono else "專業、莊重、合乎法庭禮儀"
                
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
                
                # Visualización Estrategia
                with st.expander("🧠 AI 策略分析 (Strategy)", expanded=True):
                    st.markdown(f"**核心爭點:** {analisis.get('status_causae')}")
                    st.markdown(f"**防禦策略:** {analisis.get('estrategia_defensa')}")

                # Visualización Texto
                titulo = doc_final.get('titulo', '法律書狀')
                texto = doc_final.get('texto_completo', '')
                
                st.markdown(f"#### {titulo}")
                st.markdown(f"**致：{receptor}**") # Mostramos el receptor arriba
                st.code(texto, language=None)
                
                # Botón Descarga
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
st.caption(f"系統狀態：線上 | 剩餘試用次數：{MAX_CALLS - st.session_state.api_calls}/{MAX_CALLS} | 模型：Gemini 2.0 Flash Lite")
