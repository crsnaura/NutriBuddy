import streamlit as st
import pandas as pd
from rapidfuzz import process
import re

# --- 1. INITIAL SETTINGS ---
for key in ["messages", "total_kalori_harian", "daftar_makan_harian", "pending_options", "last_qty"]:
    if key not in st.session_state:
        if key == "total_kalori_harian": st.session_state[key] = 0.0
        elif key == "last_qty": st.session_state[key] = 1.0
        elif key == "messages" or key == "daftar_makan_harian": st.session_state[key] = []
        else: st.session_state[key] = None

st.set_page_config(page_title="NutriBuddy AI", page_icon="🥗", layout="centered")

# --- 2. CSS CUSTOM (TOTAL RECALL - PERSIS SS KAMU) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif&family=Inter:wght@400;500;600&display=swap');
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    .stApp { background: linear-gradient(135deg, #fdfcfd 0%, #f5f0ff 100%); font-family: 'Inter', sans-serif; }
    
    .top-header { position: fixed; top: 0; left: 0; width: 100%; padding: 15px 30px; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(20px); z-index: 999; font-weight: 600; font-size: 18px; color: #4c1d95; border-bottom: 1px solid rgba(139, 92, 246, 0.1); }
    
    .main .block-container { padding-top: 100px; padding-bottom: 130px; max-width: 650px; }
    
    .hero-text { font-family: 'Instrument Serif', serif; font-size: 52px; color: #2e1065; line-height: 1.1; margin-bottom: 8px; text-align: center; }
    .hero-subtext { color: #6b21a8; font-size: 18px; margin-bottom: 40px; text-align: center; opacity: 0.8; }
    
    .chat-row { display: flex; margin: 18px 0; width: 100%; animation: fadeIn 0.4s ease-out; }
    .row-user { justify-content: flex-end; }
    .row-bot { justify-content: flex-start; }
    
    .bubble-user { background: #8b5cf6; color: white; padding: 12px 22px; border-radius: 24px 24px 4px 24px; box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2); max-width: 85%; }
    .bubble-bot { background: rgba(255, 255, 255, 0.85); color: #1e1b4b; padding: 16px 22px; border-radius: 4px 24px 24px 24px; border: 1px solid rgba(139, 92, 246, 0.2); backdrop-filter: blur(12px); box-shadow: 0 4px 20px rgba(0,0,0,0.03); max-width: 85%; }

    div.stButton > button { background: white; border: 1px solid rgba(139, 92, 246, 0.15); border-radius: 20px; padding: 15px 20px; color: #4c1d95; transition: all 0.25s ease; font-weight: 500; width: 100%; }
    div.stButton > button:hover { border-color: #8b5cf6; background: #fdfaff; transform: translateY(-3px); box-shadow: 0 8px 20px rgba(139, 92, 246, 0.08); }

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
        mapping = {'name': 'nama', 'calories': 'kalori', 'proteins': 'protein', 'fat': 'lemak', 'carbohydrate': 'karbo', 'karbohidrat': 'karbo'}
        df = df.rename(columns=mapping)
        df["nama"] = df["nama"].astype(str).str.lower()
        return df
    except: return pd.DataFrame()

df = load_data()

# --- 4. LOGIKA PINTAR ---
def get_nutrition_response(food_name, qty=1.0):
    row = df[df["nama"] == food_name].iloc[0]
    kalori = row['kalori'] * qty
    protein = row['protein'] * qty
    lemak = row['lemak'] * qty
    karbo = row['karbo'] * qty
    st.session_state.total_kalori_harian += kalori
    st.session_state.daftar_makan_harian.append(f"{food_name.title()} ({qty}x)")
    
    return (f"✅ Dicatat: **{food_name.title()}** ({qty} porsi)\n\n"
            f"Total energi: **{kalori:.0f} kkal**\n"
            f"*(Estimasi {qty} porsi × 100g)*\n\n"
            f"**Rincian Gizi:**\n"
            f"• Karbo: {karbo:.1f}g\n"
            f"• Protein: {protein:.1f}g\n"
            f"• Lemak: {lemak:.1f}g\n\n"
            f"⚠️ *Catatan: Data dihitung per 100 gram per porsi.*")

def process_input(text):
    text_raw = text.lower()
    if any(k in text_raw for k in ["total", "jumlah", "riwayat"]):
        total = st.session_state.total_kalori_harian
        riwayat = ", ".join(st.session_state.daftar_makan_harian) if st.session_state.daftar_makan_harian else "Kosong"
        return f"Total asupan: **{total:.0f} kkal**.\n\nRiwayat: {riwayat}.", None

    segments = re.split(r' dan |,| dan', text_raw)
    all_responses = []
    
    for seg in segments:
        qty_match = re.search(r'(\d+)\s*porsi', seg)
        qty = float(qty_match.group(1)) if qty_match else 1.0
        query = re.sub(r'\d+|makan|porsi|tadi|habis|beli|dan|saya|aku|mau', '', seg).strip()
        if not query: continue
        
        # LOGIKA AYAM: Ambil semua yang mirip
        matches = process.extract(query, df["nama"].tolist(), limit=5)
        
        # Jika cuma ada 1 yang mirip banget (>98%), langsung hajar
        if matches and matches[0][1] > 98 and len([m for m in matches if m[1] > 80]) == 1:
            all_responses.append(get_nutrition_response(matches[0][0], qty))
        # Jika ada banyak pilihan (seperti ayam goreng, ayam bakar, dll), nanya!
        elif matches and matches[0][1] > 60:
            st.session_state.last_qty = qty
            return "Maksud kamu yang mana nih? Pilih salah satu ya!", [m[0] for m in matches]
        else:
            all_responses.append(f"❓ Aduh, aku ngga nemu '{query}'.")

    return "\n\n---\n\n".join(all_responses) if all_responses else "Coba sebutkan nama makanannya ya!", None

# --- 5. UI RENDER ---

# Progress Bar
if st.session_state.total_kalori_harian > 0:
    prog = min(st.session_state.total_kalori_harian / 2000, 1.0)
    st.write(f"**Harian: {st.session_state.total_kalori_harian:.0f} / 2000 kkal**")
    st.progress(prog)

main_area = st.container()
with main_area:
    if not st.session_state.messages:
        st.markdown("<div class='hero-text'>Hello!</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtext'>Sudah makan apa aja hari ini?</div>", unsafe_allow_html=True)
        
        _, col_s, _ = st.columns([0.1, 4, 0.1])
        with col_s:
            s1, s2 = st.columns(2)
            saran = [("Ayam Ampla Goreng 🍳", "ayam ampla goreng"), ("Geprek Mba Rara 🍗", "ayam geprek"), 
                     ("Mie Ayam 🍜", "mie ayam"), ("Martabak Telur 🥪", "martabak telur")]
            for idx, (label, q) in enumerate(saran):
                with (s1 if idx % 2 == 0 else s2):
                    if st.button(label, key=f"s_{idx}"):
                        st.session_state.messages.append({"role": "user", "content": label})
                        ans, opts = process_input(q)
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                        st.session_state.pending_options = opts
                        st.rerun()

    for msg in st.session_state.messages:
        side = "row-user" if msg["role"] == "user" else "row-bot"
        bubble = "bubble-user" if msg["role"] == "user" else "bubble-bot"
        st.markdown(f'<div class="chat-row {side}"><div class="{bubble}">{msg["content"]}</div></div>', unsafe_allow_html=True)

    if st.session_state.pending_options:
        st.markdown("<div style='text-align: center; margin-top: 20px; font-weight: 600; color: #4c1d95;'>Pilih salah satu ya:</div>", unsafe_allow_html=True)
        _, f_col, _ = st.columns([0.1, 4, 0.1])
        with f_col:
            f1, f2 = st.columns(2)
            for i, opt in enumerate(st.session_state.pending_options):
                with (f1 if i % 2 == 0 else f2):
                    if st.button(opt.title(), key=f"f_{i}"):
                        st.session_state.messages.append({"role": "user", "content": opt.title()})
                        res = get_nutrition_response(opt, st.session_state.last_qty)
                        st.session_state.messages.append({"role": "assistant", "content": res})
                        st.session_state.pending_options = None
                        st.rerun()

prompt = st.chat_input("Tanya NutriBuddy...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    ans, opts = process_input(prompt)
    st.session_state.messages.append({"role": "assistant", "content": ans})
    st.session_state.pending_options = opts
    st.rerun()
