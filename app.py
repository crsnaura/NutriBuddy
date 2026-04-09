import streamlit as st
import pandas as pd
from rapidfuzz import process
from collections import Counter
import re

# --- 1. INITIAL SETTINGS ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_kalori_harian" not in st.session_state:
    st.session_state.total_kalori_harian = 0.0
if "daftar_makan_harian" not in st.session_state:
    st.session_state.daftar_makan_harian = []
if "pending_options" not in st.session_state:
    st.session_state.pending_options = None

st.set_page_config(page_title="NutriBuddy AI", page_icon="🥗", layout="centered")

# --- 2. CSS CUSTOM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif&family=Inter:wght@400;500;600&display=swap');
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background: linear-gradient(135deg, #fdfcfd 0%, #f5f0ff 100%); font-family: 'Inter', sans-serif; }
    .top-header { position: fixed; top: 0; left: 0; width: 100%; padding: 15px 30px; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(20px); z-index: 999; font-weight: 600; font-size: 18px; color: #4c1d95; border-bottom: 1px solid rgba(139, 92, 246, 0.1); }
    .main .block-container { padding-top: 100px; padding-bottom: 130px; max-width: 650px; }
    .hero-text { font-family: 'Instrument Serif', serif; font-size: 52px; color: #2e1065; line-height: 1.1; margin-bottom: 8px; }
    .chat-row { display: flex; margin: 18px 0; width: 100%; animation: fadeIn 0.4s ease-out; }
    .row-user { justify-content: flex-end; }
    .row-bot { justify-content: flex-start; }
    .bubble-user { background: #8b5cf6; color: white; padding: 12px 22px; border-radius: 24px 24px 4px 24px; box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2); max-width: 85%; }
    .bubble-bot { background: rgba(255, 255, 255, 0.85); color: #1e1b4b; padding: 16px 22px; border-radius: 4px 24px 24px 24px; border: 1px solid rgba(139, 92, 246, 0.2); backdrop-filter: blur(12px); box-shadow: 0 4px 20px rgba(0,0,0,0.03); max-width: 85%; line-height: 1.5; }
    div.stButton > button { background: white; border: 1px solid rgba(139, 92, 246, 0.15); border-radius: 20px; padding: 10px 15px; color: #4c1d95; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="top-header">NutriBuddy</div>', unsafe_allow_html=True)

# --- 3. DATA LOAD ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("nutrition.csv")
        df.columns = df.columns.str.strip().str.lower()
        if 'name' in df.columns:
            df = df.rename(columns={"name": "nama", "calories": "kalori", "proteins": "protein", "fat": "lemak", "carbohydrate": "karbohidrat"})
        df["nama"] = df["nama"].astype(str).str.lower()
        return df
    except: return pd.DataFrame()

df = load_data()

# --- 4. LOGIKA PINTAR ---
def get_nutrition_info(food_name, qty=1.0):
    """Hanya mengambil data tanpa menambah ke session state (untuk multisearch)"""
    try:
        row = df[df["nama"] == food_name].iloc[0]
        return {
            "nama": food_name.title(),
            "kalori": row['kalori'] * qty,
            "protein": row['protein'] * qty,
            "lemak": row['lemak'] * qty,
            "karbo": row['karbohidrat'] * qty,
            "qty": qty
        }
    except: return None

def clean_segment(text):
    stopwords = ["makan", "minum", "saya", "tadi", "porsi", "habis", "beli", "dan"]
    query = text.lower()
    qty_match = re.search(r'(\d+)\s*porsi', query)
    qty = float(qty_match.group(1)) if qty_match else 1.0
    query = re.sub(r'\d+', '', query)
    words = [w for w in query.split() if w not in stopwords]
    return " ".join(words), qty

def process_input(text):
    text_raw = text.lower()
    
    # Summary Check
    if any(k in text_raw for k in ["total", "jumlah", "kurang", "sisa", "riwayat"]):
        total = st.session_state.total_kalori_harian
        ringkasan = ", ".join(st.session_state.daftar_makan_harian) if st.session_state.daftar_makan_harian else "Kosong"
        return f"Total: **{total:.0f} kkal**.\n\nRiwayat: {ringkasan}.", None

    # Multisearch Logic (Split by 'dan' or ',')
    segments = re.split(r' dan |,| dan', text_raw)
    all_responses = []
    pending_to_ask = []

    for seg in segments:
        query, qty = clean_segment(seg)
        if not query.strip(): continue
        
        matches = process.extract(query, df["nama"].tolist(), limit=3)
        if matches and matches[0][1] > 90:
            info = get_nutrition_info(matches[0][0], qty)
            st.session_state.total_kalori_harian += info['kalori']
            st.session_state.daftar_makan_harian.append(f"{info['nama']} ({qty}x)")
            all_responses.append(f"• **{info['nama']}** ({qty}x100g): {info['kalori']:.0f} kkal")
        else:
            pending_to_ask.append(query)

    if pending_to_ask:
        # Jika ada yang tidak jelas, tanya satu per satu (prioritas item pertama)
        matches = process.extract(pending_to_ask[0], df["nama"].tolist(), limit=5)
        return "Ada yang kurang jelas nih, maksud kamu yang mana?", [m[0] for m in matches if m[1] > 60]

    if all_responses:
        return "Berhasil mencatat:\n" + "\n".join(all_responses) + "\n\n*Data berbasis 100g per porsi.*", None
    
    return "Duh, aku ngga paham. Coba sebutkan nama makanannya ya!", None

# --- 5. TAMPILAN UTAMA ---
# --- PROGRESS VISUALIZATION ---
if st.session_state.total_kalori_harian > 0:
    target = 2000
    progress = min(st.session_state.total_kalori_harian / target, 1.0)
    color = "🔴" if st.session_state.total_kalori_harian > target else "🟣"
    st.markdown(f"**Harian: {st.session_state.total_kalori_harian:.0f} / {target} kkal {color}**")
    st.progress(progress)

main_container = st.container()
with main_container:
    if not st.session_state.messages:
        st.markdown("<div class='hero-text'>Hello!</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtext'>Sudah makan apa hari ini? Bisa sebutkan beberapa sekaligus, lho!</div>", unsafe_allow_html=True)
    
    for msg in st.session_state.messages:
        side, bubble = ("row-user", "bubble-user") if msg["role"] == "user" else ("row-bot", "bubble-bot")
        st.markdown(f'<div class="chat-row {side}"><div class="{bubble}">{msg["content"]}</div></div>', unsafe_allow_html=True)

    if st.session_state.pending_options:
        cols = st.columns(len(st.session_state.pending_options))
        for i, opt in enumerate(st.session_state.pending_options):
            with cols[i]:
                if st.button(opt.title(), key=f"c_{i}"):
                    st.session_state.messages.append({"role": "user", "content": opt})
                    # Simpan pilihan manual
                    info = get_nutrition_info(opt, 1.0)
                    st.session_state.total_kalori_harian += info['kalori']
                    st.session_state.daftar_makan_harian.append(info['nama'])
                    st.session_state.messages.append({"role": "assistant", "content": f"Sip! {info['nama']} sudah dicatat."})
                    st.session_state.pending_options = None
                    st.rerun()

prompt = st.chat_input("Contoh: makan 2 porsi sate dan 1 porsi nasi")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    jawaban, options = process_input(prompt)
    st.session_state.messages.append({"role": "assistant", "content": jawaban})
    st.session_state.pending_options = options
    st.rerun()
