import streamlit as st
import pandas as pd
from rapidfuzz import process
from collections import Counter
import re

# =============================
# 1. SESSION STATE
# =============================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_kalori_harian" not in st.session_state:
    st.session_state.total_kalori_harian = 0.0
if "daftar_makan_harian" not in st.session_state:
    st.session_state.daftar_makan_harian = []
if "pending_options" not in st.session_state:
    st.session_state.pending_options = None

st.set_page_config(page_title="NutriBuddy AI", page_icon="🥗", layout="centered")

# =============================
# 2. LOAD DATA
# =============================
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
# 3. NLP - ENTITY EXTRACTION
# =============================
def extract_entities(text, food_list):
    text = text.lower()

    # ambil angka (quantity)
    quantities = re.findall(r'\d+', text)
    quantity = int(quantities[0]) if quantities else 1

    detected_foods = []
    words = text.split()

    # sliding window (1–3 kata)
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

# =============================
# 4. RESPONSE GENERATOR
# =============================
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

# =============================
# 5. MAIN NLP PROCESSING
# =============================
def process_input(text):
    text = text.lower()

    # ===== INTENT: TOTAL =====
    if any(k in text for k in ["total", "jumlah", "sisa"]):
        total = st.session_state.total_kalori_harian

        if not st.session_state.daftar_makan_harian:
            return "Kamu belum makan apa-apa hari ini.", None

        counts = Counter(st.session_state.daftar_makan_harian)
        ringkasan = ", ".join([f"{name} ({qty}x)" for name, qty in counts.items()])

        pesan = f"Total asupanmu: **{total:.0f} kkal**.\n\nRiwayat: {ringkasan}"

        if total > 2000:
            pesan += "\n\n⚠️ _Sudah melebihi 2000 kkal, jangan lupa olahraga ya!_"

        return pesan, None

    # ===== ENTITY EXTRACTION =====
    food_list = df["nama"].tolist()
    entities = extract_entities(text, food_list)

    if not entities["foods"]:
        return "Aku belum ngerti makanan yang kamu maksud 😢", None

    # ===== GENERATE MULTI RESPONSE =====
    responses = []
    for food in entities["foods"]:
        responses.append(get_nutrition_response(food, entities["quantity"]))

    return "\n\n".join(responses), None

# =============================
# 6. UI (STREAMLIT)
# =============================
st.title("🥗 NutriBuddy AI")

# tampilkan chat
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

# input user
prompt = st.chat_input("Tanya makananmu...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    response, options = process_input(prompt)

    st.session_state.messages.append({"role": "assistant", "content": response})

    st.rerun()
