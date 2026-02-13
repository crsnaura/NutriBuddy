import streamlit as st
import pandas as pd
import re

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

def nutribuddy_response(text):

    detected = []

    for food in df["nama"]:
        if food in text:
            qty = 1

            match = re.search(rf"{food}\s*(\d+)", text)
            if match:
                qty = int(match.group(1))

            detected.append((food, qty))

    if len(detected) == 0:
        return "Maaf ya, aku belum nemu makanan itu di database 😢"

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
