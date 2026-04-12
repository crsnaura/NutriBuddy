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

# --- 2. CSS (TETAP SAMA) ---
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
        padding: 10px 20px; 
        color: #4c1d95;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="top-header">NutriBuddy</div>', unsafe_allow_html=True)

# --- 3. DATA LOAD ---
@st.cache_data
def load_data():
    df = pd.read_csv("nutrition.csv")
    df.columns = df.columns.str.lower()
    df = df.rename(columns={
        "name": "nama",
        "calories": "kalori",
        "proteins": "protein",
        "fat": "lemak",
        "carbohydrate": "karbohidrat"
    })
    df["nama"] = df["nama"].str.lower()
    return df

df = load_data()

# =============================
# 🔥 NLP / NER UPGRADE
# =============================
def extract_entities(text, food_list):
    text = text.lower()

    # ambil quantity
    quantities = re.findall(r'\d+', text)
    quantity = int(quantities[0]) if quantities else 1

    detected_foods = []
    words = text.split()

    for i in range(len(words)):
        for j in range(i+1, min(i+4, len(words)+1)):
            phrase = " ".join(words[i:j])
            match = process.extractOne(phrase, food_list)
            if match and match[1] > 85:
                detected_foods.append(match[0])

    return {
        "foods": list(set(detected_foods)),
        "quantity": quantity
    }

# --- RESPONSE ---
def get_nutrition_response(food_name, quantity=1):
    data = df[df["nama"] == food_name].iloc[0]

    kalori = data['kalori'] * quantity
    protein = data['protein'] * quantity
    lemak = data['lemak'] * quantity
    karbo = data['karbohidrat'] * quantity

    st.session_state.total_kalori_harian += kalori

    for _ in range(quantity):
        st.session_state.daftar_makan_harian.append(food_name.title())

    return (
        f"✅ Dicatat: {food_name.title()} ({quantity} porsi)\n\n"
        f"Total Energi: {kalori:.0f} kkal\n\n"
        f"Rincian Gizi:\n"
        f"Karbo {karbo:.1f}g, Protein {protein:.1f}g, Lemak {lemak:.1f}g\n\n"
        f"---\n"
        f"⚠️ _Perhitungan berdasarkan 100 gram per porsi._"
    )

# --- PROCESS ---
def process_input(text):
    text = text.lower()

    # intent total
    if any(k in text for k in ["total", "jumlah", "sisa"]):
        total = st.session_state.total_kalori_harian

        if not st.session_state.daftar_makan_harian:
            return "Kamu belum makan apa-apa hari ini.", None

        counts = Counter(st.session_state.daftar_makan_harian)
        ringkasan = ", ".join([f"{name} ({qty}x)" for name, qty in counts.items()])

        pesan = f"Total asupanmu: **{total:.0f} kkal**.\n\nRiwayat: {ringkasan}"

        if total > 2000:
            pesan += "\n\n⚠️ _Sudah melebihi 2000 kkal!_"

        return pesan, None

    # NLP extraction
    food_list = df["nama"].tolist()
    entities = extract_entities(text, food_list)

    if not entities["foods"]:
        return "Aku belum ngerti makanan kamu 😢", None

    responses = []
    for food in entities["foods"]:
        responses.append(get_nutrition_response(food, entities["quantity"]))

    return "\n\n".join(responses), None

# --- UI ---
main_container = st.container()

with main_container:
    for msg in st.session_state.messages:
        side, bubble = ("row-user", "bubble-user") if msg["role"] == "user" else ("row-bot", "bubble-bot")
        st.markdown(f'<div class="chat-row {side}"><div class="{bubble}">{msg["content"]}</div></div>', unsafe_allow_html=True)

prompt = st.chat_input("Tanya NutriBuddy...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    jawaban, options = process_input(prompt)
    st.session_state.messages.append({"role": "assistant", "content": jawaban})
    st.rerun()
