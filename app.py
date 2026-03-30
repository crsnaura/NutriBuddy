import streamlit as st
import pandas as pd
import re
from rapidfuzz import process, fuzz

# ================= UI CONFIG =================
st.set_page_config(page_title="NutriBuddy", page_icon="🥗")

# Custom CSS (PINK THEME 💖)
st.markdown("""
    <style>
    body {
        background-color: #fff0f5;
    }
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
    }
    .stChatMessage.user {
        background-color: #ffe4ec;
    }
    .stChatMessage.assistant {
        background-color: #f8c8dc;
    }
    .stButton>button {
        background-color: #ff69b4;
        color: white;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ================= LOAD DATA =================
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

# ================= HEADER =================
st.title("🥗 NutriBuddy")
st.caption("Asisten pintar penghitung kalori makanan 💖")

# ================= CHAT INIT =================
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if len(st.session_state["messages"]) == 0:
    welcome = "Halo! Aku NutriBuddy 🥗💖\nCeritakan makanan yang kamu makan hari ini ya!"
    st.session_state["messages"].append({"role": "assistant", "content": welcome})

# ================= DISPLAY CHAT =================
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# ================= INPUT =================
prompt = st.chat_input("Contoh: nasi goreng 2, ayam 1")

# ================= NLP FUNCTIONS =================
def extract_foods(text, food_list):
    detected = []

    # Split berdasarkan koma / "dan"
    items = re.split(r",|dan", text)

    for item in items:
        item = item.strip()

        # Ambil angka (qty)
        qty_match = re.search(r"(\d+)", item)
        qty = int(qty_match.group(1)) if qty_match else 1

        # Hapus angka dari teks
        clean_item = re.sub(r"\d+", "", item).strip()

        # Fuzzy match (lebih kuat)
        match = process.extractOne(
            clean_item,
            food_list,
            scorer=fuzz.WRatio
        )

        if match and match[1] > 75:
            detected.append((match[0], qty))

    return detected


def nutribuddy_response(text):
    detected = extract_foods(text, df["nama"].tolist())

    if len(detected) == 0:
        return "Maaf ya 😢 aku belum kenal makanan itu. Coba tulis yang lebih umum ya!"

    rows = []

    for food, qty in detected:
        row = df[df["nama"] == food].copy()
        row["qty"] = qty

        row["kalori"] *= qty
        row["protein"] *= qty
        row["lemak"] *= qty
        row["karbohidrat"] *= qty

        rows.append(row)

    result = pd.concat(rows)

    # ================= DISPLAY TABLE =================
    st.dataframe(
        result[["nama","qty","kalori","protein","lemak","karbohidrat"]],
        use_container_width=True
    )

    # ================= TOTAL =================
    total_kalori = result["kalori"].sum()
    total_lemak = result["lemak"].sum()
    total_protein = result["protein"].sum()
    total_karbo = result["karbohidrat"].sum()

    response = "Aku catat ya 💖:\n\n"

    for f, q in detected:
        response += f"- {f} ({q} porsi)\n"

    response += f"""
🔥 Kalori: {total_kalori:.0f} kkal  
🥩 Protein: {total_protein:.1f} g  
🧈 Lemak: {total_lemak:.1f} g  
🍚 Karbohidrat: {total_karbo:.1f} g  
"""

    # ================= SMART FEEDBACK =================
    if total_lemak > 40:
        response += "\n⚠️ Lemak cukup tinggi, coba next meal pilih yang direbus ya!"
    elif total_karbo > 80:
        response += "\n⚠️ Karbo agak tinggi, tambahin protein biar balance!"
    else:
        response += "\n✅ Asupan kamu udah cukup seimbang!"

    return response


# ================= RUN =================
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    reply = nutribuddy_response(prompt.lower())

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.chat_message("assistant").write(reply)
