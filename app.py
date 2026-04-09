import streamlit as st
import pandas as pd
from rapidfuzz import process
from collections import Counter

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

# --- 2. CSS CUSTOM (HARMONIZED PURPLE THEME) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif&family=Inter:wght@400;500;600&display=swap');
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    .stApp { 
        background: linear-gradient(135deg, #fdfcfd 0%, #f5f0ff 100%);
        font-family: 'Inter', sans-serif; 
    }

    .top-header { 
        position: fixed; top: 0; left: 0; width: 100%; padding: 15px 30px; 
        background: rgba(255, 255, 255, 0.7); 
        backdrop-filter: blur(20px); 
        z-index: 999; 
        font-weight: 600; 
        font-size: 18px; 
        color: #4c1d95;
        border-bottom: 1px solid rgba(139, 92, 246, 0.1); 
    }

    .main .block-container {
        padding-top: 100px;
        padding-bottom: 130px;
        max-width: 650px;
    }

    .hero-text {
        font-family: 'Instrument Serif', serif;
        font-size: 52px;
        color: #2e1065;
        line-height: 1.1;
        margin-bottom: 8px;
    }
    
    .hero-subtext {
        color: #6b21a8;
        font-size: 18px;
        margin-bottom: 40px;
        opacity: 0.8;
    }

    .chat-row { display: flex; margin: 18px 0; width: 100%; animation: fadeIn 0.4s ease-out; }
    .row-user { justify-content: flex-end; }
    .row-bot { justify-content: flex-start; }
    
    .bubble-user { 
        background: #8b5cf6; 
        color: white; 
        padding: 12px 22px; 
        border-radius: 24px 24px 4px 24px; 
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2);
        max-width: 85%;
    }
    
    .bubble-bot { 
        background: rgba(255, 255, 255, 0.85); 
        color: #1e1b4b; 
        padding: 16px 22px; 
        border-radius: 4px 24px 24px 24px; 
        border: 1px solid rgba(139, 92, 246, 0.2); 
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
        max-width: 85%;
        line-height: 1.5;
    }

    div.stButton > button { 
        background: white; 
        border: 1px solid rgba(139, 92, 246, 0.15); 
        border-radius: 20px; 
        padding: 15px 20px; 
        color: #4c1d95;
        transition: all 0.25s ease;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    div.stButton > button:hover { 
        border-color: #8b5cf6;
        background: #fdfaff;
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(139, 92, 246, 0.08);
    }

    .stChatInputContainer {
        padding-bottom: 30px !important;
        background: transparent !important;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="top-header">NutriBuddy</div>', unsafe_allow_html=True)

# --- 3. DATA LOAD ---
@st.cache_data
def load_data():
    path = "C:/Users/Aul/Downloads/nutribuddyantirevisi/nutrition.csv"
    try:
        df = pd.read_csv(path)
        df.columns = df.columns.str.lower()
        df = df.rename(columns={"name": "nama", "calories": "kalori", "proteins": "protein", "fat": "lemak", "carbohydrate": "karbohidrat"})
        df["nama"] = df["nama"].str.lower()
        return df
    except: return pd.DataFrame()

df = load_data()

# --- 4. LOGIKA PINTAR ---
def get_nutrition_response(food_name, kalori=None, protein=None, lemak=None):
    if kalori is None:
        data = df[df["nama"] == food_name].iloc[0]
        kalori = data['kalori']
        protein = f"{data['protein']:.1f}g"
        lemak = f"{data['lemak']:.1f}g"
        karbo = f"{data['karbohidrat']:.1f}g"
    else:
        karbo = "-"

    st.session_state.total_kalori_harian += kalori
    st.session_state.daftar_makan_harian.append(food_name.title())
    
    return (f"Total kalori {food_name.title()} adalah {kalori:.0f} kkal\n\n"
             f"Dengan Rincian Gizi:\n"
             f"Karbo: {karbo} | Protein: {protein} | Lemak: {lemak}")

def process_input(text):
    text = text.lower()
    if any(k in text for k in ["total", "jumlah", "kurang", "sisa"]):
        total = st.session_state.total_kalori_harian
        if not st.session_state.daftar_makan_harian:
            return "Kamu belum makan apa-apa hari ini.", None
        counts = Counter(st.session_state.daftar_makan_harian)
        ringkasan = ", ".join([f"{name} ({qty}x)" for name, qty in counts.items()])
        pesan = f"Total asupanmu: **{total:.0f} kkal**.\n\nRiwayat: {ringkasan}."
        if total > 2000:
            pesan += "\n\n⚠️ Wah, sudah lewat 2000 kkal! Jangan lupa olahraga ya!"
        return pesan, None

    if "rara" in text:
        return get_nutrition_response("Ayam Geprek Mba Rara", 246, "28g", "17g"), None

    food_list = df["nama"].tolist()
    matches = process.extract(text, food_list, limit=5)
    high_matches = [m[0] for m in matches if m[1] > 80]
    
    if not high_matches: return "Duh, aku ngga nemu makanan itu. Coba sebut yang lain ya!", None
    if matches[0][1] > 95: return get_nutrition_response(matches[0][0]), None
    
    return "Maksud kamu yang mana nih? Pilih salah satu ya!", high_matches

# --- 5. TAMPILAN UTAMA ---
main_container = st.container()

with main_container:
    if not st.session_state.messages:
        st.markdown("<div class='hero-text'>Hello!</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtext'>Sudah makan apa aja hari ini?</div>", unsafe_allow_html=True)
        
        # Buffer untuk tampilan awal agar tidak terlalu lebar
        _, saran_col, _ = st.columns([0.1, 4, 0.1])
        with saran_col:
            sub_cols = st.columns(2)
            saran = [("Ayam Ampla Goreng 🍳", "ayam ampla goreng"), ("Geprek Mba Rara 🍗", "rara"), ("Mie Ayam 🍜", "mie ayam"), ("Martabak Telur 🥪", "martabak telur")]
            for i, (label, query) in enumerate(saran):
                with sub_cols[i % 2]:
                    if st.button(label, key=f"s_start_{i}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": label})
                        jawaban, options = process_input(query)
                        st.session_state.messages.append({"role": "assistant", "content": jawaban})
                        st.session_state.pending_options = options
                        st.rerun()
    
    for msg in st.session_state.messages:
        side, bubble = ("row-user", "bubble-user") if msg["role"] == "user" else ("row-bot", "bubble-bot")
        st.markdown(f'<div class="chat-row {side}"><div class="{bubble}">{msg["content"]}</div></div>', unsafe_allow_html=True)

    # Render Pilihan Fuzzy (VERSI FIX POSISI TENGAH)
    if st.session_state.pending_options:
        st.markdown("<div style='text-align: center; opacity: 0.5; margin: 20px 0 10px 0;'>— Pilih salah satu ya —</div>", unsafe_allow_html=True)
        
        # Buffer kiri dan kanan (1) supaya kolom tengah (3) jadi pusat perhatian
        _, center_area, _ = st.columns([1, 3, 1])
        with center_area:
            n_opt = len(st.session_state.pending_options)
            opt_cols = st.columns(n_opt)
            for i, opt in enumerate(st.session_state.pending_options):
                with opt_cols[i]:
                    if st.button(opt.title(), key=f"choice_{i}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": opt})
                        st.session_state.messages.append({"role": "assistant", "content": get_nutrition_response(opt)})
                        st.session_state.pending_options = None
                        st.rerun()

prompt = st.chat_input("Tanya NutriBuddy...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    jawaban, options = process_input(prompt)
    st.session_state.messages.append({"role": "assistant", "content": jawaban})
    st.session_state.pending_options = options
    st.rerun()
