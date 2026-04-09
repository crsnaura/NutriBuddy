import streamlit as st
import pandas as pd
from rapidfuzz import process
from collections import Counter
import re

# --- 1. INITIAL SETTINGS ---
for key in ["messages", "total_kalori_harian", "daftar_makan_harian", "pending_options", "last_qty"]:
    if key not in st.session_state:
        if key == "total_kalori_harian": st.session_state[key] = 0.0
        elif key == "last_qty": st.session_state[key] = 1.0
        elif key == "messages" or key == "daftar_makan_harian": st.session_state[key] = []
        else: st.session_state[key] = None

st.set_page_config(page_title="NutriBuddy AI", page_icon="🥗", layout="centered")

# --- 2. CSS CUSTOM (STETIK PARAH) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif&family=Inter:wght@400;500;600&display=swap');
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background: linear-gradient(135deg, #fdfcfd 0%, #f5f0ff 100%); font-family: 'Inter', sans-serif; }
    .top-header { position: fixed; top: 0; left: 0; width: 100%; padding: 15px 30px; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(20px); z-index: 999; font-weight: 600; font-size: 18px; color: #4c1d95; border-bottom: 1px solid rgba(139, 92, 246, 0.1); }
    .main .block-container { padding-top: 80px; padding-bottom: 120px; max-width: 650px; }
    .hero-text { font-family: 'Instrument Serif', serif; font-size: 64px; color: #2e1065; line-height: 1.1; margin-bottom: 10px; text-align: center; }
    .hero-subtext { color: #6b21a8; font-size: 20px; margin-bottom: 40px; text-align: center; opacity: 0.8; }
    .chat-row { display: flex; margin: 18px 0; width: 100%; animation: fadeIn 0.4s ease-out; }
    .row-user { justify-content: flex-end; }
    .row-bot { justify-content: flex-start; }
    .bubble-user { background: #8b5cf6; color: white; padding: 12px 22px; border-radius: 24px 24px 4px 24px; box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2); max-width: 85%; }
    .bubble-bot { background: rgba(255, 255, 255, 0.85); color: #1e1b4b; padding: 16px 22px; border-radius: 4px 24px 24px 24px; border: 1px solid rgba(139, 92, 246, 0.2); backdrop-filter: blur(12px); box-shadow: 0 4px 20px rgba(0,0,0,0.03); max-width: 85%; }
    div.stButton > button { background: white; border: 1px solid rgba(139, 92, 246, 0.15); border-radius: 15px; padding: 15px 20px; color: #4c1d95; font-weight: 500; transition: all 0.2s; width: 100%; }
    div.stButton > button:hover { border-color: #8b5cf6; background: #fdfaff; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(139, 92, 246, 0.1); }
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
        if 'name' in df.columns: df = df.rename(columns={"name": "nama"})
        df["nama"] = df["nama"].astype(str).str.lower()
        return df
    except: return pd.DataFrame()

df = load_data()

# --- 4. LOGIKA UTAMA ---
def get_nutrition_response(food_name, qty=1.0):
    row = df[df["nama"] == food_name].iloc[0]
    kalori = row['calories'] * qty
    st.session_state.total_kalori_harian += kalori
    st.session_state.daftar_makan_harian.append(f"{food_name.title()} ({qty}x)")
    return f"✅ **{food_name.title()}** ({qty}x100g) berhasil dicatat! +{kalori:.0f} kkal."

def process_input(text):
    text_raw = text.lower()
    if any(k in text_raw for k in ["total", "jumlah", "sisa", "riwayat"]):
        total = st.session_state.total_kalori_harian
        riwayat = ", ".join(st.session_state.daftar_makan_harian) if st.session_state.daftar_makan_harian else "Belum ada"
        return f"Total asupanmu: **{total:.0f} kkal**.\n\nRiwayat: {riwayat}.", None

    # Handle Multisearch
    segments = re.split(r' dan |,| dan', text_raw)
    responses = []
    
    for seg in segments:
        # Extract Qty & Clean
        qty_match = re.search(r'(\d+)\s*porsi', seg)
        qty = float(qty_match.group(1)) if qty_match else 1.0
        query = re.sub(r'\d+|makan|porsi|tadi|habis|beli|dan', '', seg).strip()
        
        if not query: continue
        
        matches = process.extract(query, df["nama"].tolist(), limit=5)
        if matches and matches[0][1] > 95:
            responses.append(get_nutrition_response(matches[0][0], qty))
        elif matches and matches[0][1] > 60:
            st.session_state.last_qty = qty
            return "Maksud kamu yang mana nih? Pilih salah satu ya!", [m[0] for m in matches]
        else:
            responses.append(f"❓ Maaf, makanan '{query}' nggak ketemu.")

    return "\n\n".join(responses) if responses else "Coba sebutkan nama makanannya ya!", None

# --- 5. UI RENDER ---

# Progress Bar di paling atas
if st.session_state.total_kalori_harian > 0:
    prog = min(st.session_state.total_kalori_harian / 2000, 1.0)
    st.write(f"**Progres Hari Ini: {st.session_state.total_kalori_harian:.0f} / 2000 kkal**")
    st.progress(prog)

# Tampilan Hero (Cuma muncul kalau belum ada chat)
if not st.session_state.messages:
    st.markdown("<div class='hero-text'>Hello!</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtext'>Sudah makan apa aja hari ini?</div>", unsafe_allow_html=True)
    
    # Tombol Saran Persis Seperti di Gambar
    c1, c2 = st.columns(2)
    saran = [("Ayam Ampla Goreng 🍳", "ayam ampla goreng"), ("Geprek Mba Rara 🍗", "ayam geprek"), 
             ("Mie Ayam 🍜", "mie ayam"), ("Martabak Telur 🥪", "martabak telur")]
    
    for i, (label, q) in enumerate(saran):
        with (c1 if i % 2 == 0 else c2):
            if st.button(label):
                st.session_state.messages.append({"role": "user", "content": label})
                ans, opts = process_input(q)
                st.session_state.messages.append({"role": "assistant", "content": ans})
                st.session_state.pending_options = opts
                st.rerun()

# Render History Chat
for msg in st.session_state.messages:
    div_class = "row-user" if msg["role"] == "user" else "row-bot"
    bub_class = "bubble-user" if msg["role"] == "user" else "bubble-bot"
    st.markdown(f'<div class="chat-row {div_class}"><div class="{bub_class}">{msg["content"]}</div></div>', unsafe_allow_html=True)

# Render PILIHAN FUZZY (Ini yang kamu cari!)
if st.session_state.pending_options:
    st.markdown("<div style='text-align: center; margin: 20px 0; color: #6b21a8; font-weight: 500;'>— Pilih salah satu ya —</div>", unsafe_allow_html=True)
    pc1, pc2 = st.columns(2)
    for i, opt in enumerate(st.session_state.pending_options):
        with (pc1 if i % 2 == 0 else pc2):
            if st.button(opt.title(), key=f"fuzzy_{i}"):
                st.session_state.messages.append({"role": "user", "content": opt.title()})
                qty = st.session_state.last_qty
                res = get_nutrition_response(opt, qty)
                st.session_state.messages.append({"role": "assistant", "content": res})
                st.session_state.pending_options = None
                st.rerun()

# Input Chat
prompt = st.chat_input("Tanya NutriBuddy...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    ans, opts = process_input(prompt)
    st.session_state.messages.append({"role": "assistant", "content": ans})
    st.session_state.pending_options = opts
    st.rerun()
