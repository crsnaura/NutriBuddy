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

def nutribuddy_response(text):
    detected = extract_foods(text, df["nama"].tolist())
    if len(detected) == 0:
        return "Maaf ya, aku belum nemu makanan itu di database 😢"
    
    foods = [item[0] for item in detected]
    qtys = [item[1] for item in detected]

    result = df[df["nama"].isin(foods)].copy()

    result["qty"] = qtys

    result["kalori"] = result["kalori"] * result["qty"]
    result["protein"] = result["protein"] * result["qty"]
    result["lemak"] = result["lemak"] * result["qty"]
    result["karbohidrat"] = result["karbohidrat"] * result["qty"]
            
    def extract_foods(text, food_list):
        detected = []
        words = text.split()
        for word in words:
            match = process.extractOne(word, food_list)
            if match:
                food_name = match[0]
                score = match[1]
                
                if score > 80:
                    qty = 1

                    qty_match = re.search(rf"{word}\s*(\d+)", text)
                    if qty_match:
                        qty = int(qty_match.group(1))

                    detected.append((food_name, qty))

        return detected
   

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
