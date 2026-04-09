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
if "last_qty" not in st.session_state:
    st.session_state.last_qty = 1.0

st.set_page_config(page_title="NutriBuddy AI", page_icon="🥗", layout="centered")

# --- 2. CSS CUSTOM (STETIK UNGU) ---
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
    div.stButton > button { background: white; border: 1px solid rgba(139, 92, 246, 0.15); border-radius: 20px; padding: 10px 20px; color: #4c1d95; font-weight: 500; transition: all 0.2s; }
    div.stButton > button:hover { border-color: #8b5cf6; background: #fdfaff; transform: translateY(-2px); }
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
def get_nutrition_response(food_name, qty=1.0):
    row = df[df["nama"] == food_name].iloc[0]
    kalori = row['kalori'] * qty
    protein = f"{row['protein'] * qty:.1f}g"
    lemak = f"{row['lemak'] * qty:.1f}g"
    karbo = f"{row['karbohidrat'] * qty:.1f}g"

    st.session_state.total_kalori_harian += kalori
    st.session_state.daftar_makan_harian.append(f"{food_name.title()} ({qty}x)")
    
    qty_label = f"**{qty:.0f} porsi** " if qty > 1 else ""
    return (f"✅ Dicatat: {qty_label}**{food_name.title()}**\n\n"
            f"Total energi: **{kalori:.0f} kkal**\n"
            f"*(Estimasi {qty} porsi × 100g)*\n\n"
            f"**Rincian Gizi:**\n"
            f"• Karbo: {karbo} | Protein: {protein} | Lemak: {lemak}\n\n"
            f"⚠️ *Catatan: Data dihitung per 100g per porsi.*")

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
    
    if any(k in text_raw for k in ["total", "jumlah", "kurang", "sisa", "riwayat"]):
        total = st.session_state.total_kalori_harian
        ringkasan = ", ".join(st.session_state.daftar_makan_harian) if st.session_state.daftar_makan_harian else "Kosong"
        return f"Total: **{total:.0f} kkal**.\n\nRiwayat: {ringkasan}.", None

    segments = re.split(r' dan |,| dan', text_raw)
    all_responses = []
    
    for seg in segments:
        query, qty = clean_segment(seg)
        if not query.strip(): continue
        
        matches = process.extract(query, df["nama"].tolist(), limit=5)
        
        # JIKA SANGAT MIRIP (>95%)
        if matches and matches[0][1] > 95:
            all_responses.append(get_nutrition_response(matches[0][0], qty))
        # JIKA AMBIGU (Butuh Pilihan)
        elif matches and matches[0][1] > 65:
            st.session_state.last_qty = qty
            return "Maksud kamu yang mana nih? Pilih salah satu ya!", [m[0] for m in matches]
        else:
            all_responses.append(f"❓ Aduh, aku ngga nemu '{query}' di database.")

    if all_responses:
        return "\n\n---\n\n".join(all_responses), None
    
    return "Duh, aku ngga paham. Coba sebutkan nama makanannya ya!", None

# --- 5. TAMPILAN UTAMA ---
# Progress Bar
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
        st.markdown("<div class='hero-subtext'>Sudah makan apa hari ini?</div>", unsafe_allow_html=True)
    
    for msg in st.session_state.messages:
        side, bubble = ("row-user", "bubble-user") if msg["role"] == "user" else ("row-bot", "bubble-bot")
        st.markdown(f'<div class="chat-row {side}"><div class="{bubble}">{msg["content"]}</div></div>', unsafe_allow_html=True)

    # Render Pilihan Fuzzy (TOMBOL PILIHAN)
    if st.session_state.pending_options:
        st.markdown("<div style='text-align: center; opacity: 0.5; margin: 20px 0 10px 0;'>— Pilih salah satu ya —</div>", unsafe_allow_html=True)
        _, center_area, _ = st.columns([0.1, 4, 0.1])
        with center_area:
            sub_cols = st.columns(2)
            for i, opt in enumerate(st.session_state.pending_options):
                with sub_cols[i % 2]:
                    if st.button(opt.title(), key=f"choice_{i}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": opt})
                        qty = st.session_state.get("last_qty", 1.0)
                        jawaban = get_nutrition_response(opt, qty)
                        st.session_state.messages.append({"role": "assistant", "content": jawaban})
                        st.session_state.pending_options = None
                        st.rerun()

prompt = st.chat_input("Tanya NutriBuddy...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    jawaban, options = process_input(prompt)
    st.session_state.messages.append({"role": "assistant", "content": jawaban})
    st.session_state.pending_options = options
    st.rerun()
