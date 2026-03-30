import streamlit as st
import pandas as pd
import re
from rapidfuzz import process

st.set_page_config(page_title="NutriBuddy", page_icon="🥗")

# Load dataset
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

st.title("🥗 NutriBuddy")
st.caption("Asisten pintar penghitung kalori makanan")

# Init chat history (WAJIB PALING ATAS)
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Greeting pertama
if len(st.session_state["messages"]) == 0:
    welcome = "Halo! Aku NutriBuddy 🥗\nCeritakan makanan yang kamu konsumsi hari ini ya!"
    st.session_state["messages"].append({"role": "assistant", "content": welcome})

# Display chat history
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Input chat
prompt = st.chat_input("Ketik makanan kamu...")

healthy_options = {
    "high_fat": ["sup sayur", "tahu kukus", "ikan rebus"],
    "high_carb": ["telur rebus", "ayam panggang", "tempe"],
    "balanced": ["buah", "yogurt", "salad"]
}
def extract_foods(text, food_list):

    stopwords = [
        "aku","saya","makan","minum","tadi","pagi",
        "siang","malam","dan","sama","pakai","porsi",
        "yang","itu","ini"
    ]

    common_words = ["daging", "ikan", "sayur", "nasi"]

    detected = []
    ambiguous_candidates = []

    words = text.split()

    for word in words:

        if word in stopwords:
            continue

        if word.isdigit():
            continue

        matches = process.extract(word, food_list, limit=5)

        # kalau kata terlalu umum → simpan kandidat
        if word in common_words:
            ambiguous_candidates = [m[0] for m in matches if m[1] > 80]
            continue

        for match in matches:
            if match[1] > 85:
                detected.append((match[0], 1))

    # deduplicate
    unique = {}
    for food, qty in detected:
        if food not in unique:
            unique[food] = qty

    detected = [(f, q) for f, q in unique.items()]

    return detected, ambiguous_candidates
def nutribuddy_response(text):

    # 👉 CEK kalau user lagi jawab pilihan
    if st.session_state["pending_choices"]:

        choice = text.strip().lower()

        if choice in st.session_state["pending_choices"]:

            detected = [(choice, 1)]
            st.session_state["pending_choices"] = None

        else:
            return "Pilih salah satu dari opsi yang aku kasih ya 🙂"

    else:

        detected, ambiguous = extract_foods(text, df["nama"].tolist())

        # 👉 kalau ambiguous → tanya balik
        if ambiguous:
            st.session_state["pending_choices"] = ambiguous

            options = "\n".join([f"- {a}" for a in ambiguous[:5]])

            return f"""
Aku belum yakin maksud kamu 🤔

Kamu maksud yang mana:
{options}

Ketik salah satu ya 🙂
"""
    
    foods = [item[0] for item in detected]
    qtys = [item[1] for item in detected]

    result = df[df["nama"].isin(foods)].copy()

    result["qty"] = qtys

    result["kalori"] = result["kalori"] * result["qty"]
    result["protein"] = result["protein"] * result["qty"]
    result["lemak"] = result["lemak"] * result["qty"]
    result["karbohidrat"] = result["karbohidrat"] * result["qty"]
    rows = []

    for food, qty in detected:
        row = df[df["nama"] == food].copy()
        row["qty"] = qty
        rows.append(row)

    result = pd.concat(rows)
    result["kalori"] *= result["qty"]
    result["protein"] *= result["qty"]
    result["lemak"] *= result["qty"]
    result["karbohidrat"] *= result["qty"]

    st.dataframe(result[["nama","qty","kalori","protein","lemak","karbohidrat"]])

    total_kalori = result["kalori"].sum()
    total_lemak = result["lemak"].sum()
    total_protein = result["protein"].sum()
    total_karbo = result["karbohidrat"].sum()

    response = f"""
Aku catat makanan ini:

"""

    for f,q in detected:
        response += f"- {f} ({q} porsi)\n"

    response += f"""

🔥 Kalori: {total_kalori:.0f} kkal  
🥩 Protein: {total_protein:.1f} g  
🧈 Lemak: {total_lemak:.1f} g  
🍚 Karbohidrat: {total_karbo:.1f} g  

"""

    if total_lemak > 30:
        response += "Karena lemak hari ini cukup tinggi, nanti malam kamu bisa pilih sayur bening atau sup ya 🙂"
    elif total_karbo > 60:
        response += "Karbohidratnya agak tinggi, seimbangkan dengan lauk berprotein ya 🙂"
    else:
        response += "Asupan kamu cukup seimbang hari ini 👍"

    return response

# Process message
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    reply = nutribuddy_response(prompt.lower())

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.chat_message("assistant").write(reply)
