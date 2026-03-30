import streamlit as st
import pandas as pd
import re
from rapidfuzz import process, fuzz

st.set_page_config(page_title="NutriBuddy", page_icon="🥗")

# ================= UI CHATGPT STYLE + PINK ACCENT =================
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background-color: #ffffff;
}

/* chat user */
[data-testid="stChatMessageContent"][aria-label="user"] {
    background-color: #ffe4ec;
    color: black;
    border-radius: 15px;
    padding: 10px;
}

/* chat bot */
[data-testid="stChatMessageContent"][aria-label="assistant"] {
    background-color: #fff;
    color: black;
    border-radius: 15px;
    padding: 10px;
    border: 1px solid #ffb6c1;
}

/* input */
textarea {
    border-radius: 10px !important;
    border: 1px solid #ff69b4 !important;
}

/* title */
h1 {
    color: #ff4da6;
    text-align: center;
}

/* caption */
p {
    text-align: center;
    color: #666;
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

df["nama"] = df["nama"].str.lower().str.strip()

# ================= HEADER =================
st.title("🥗 NutriBuddy")
st.caption("Asisten pintar penghitung kalori makanan 💖")

# ================= CHAT INIT =================
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if len(st.session_state["messages"]) == 0:
    st.session_state["messages"].append({
        "role": "assistant",
        "content": "Halo! Aku NutriBuddy 🥗💖\nCoba tulis makananmu, misalnya: *udang 2, nasi 1*"
    })

# ================= DISPLAY =================
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

prompt = st.chat_input("Ketik makanan kamu...")

# ================= NLP FIX BANGET =================
def extract_foods(text, food_list):
    detected = []

    # 🔥 ambil kata makanan aja (hapus kata ga penting)
    stopwords = ["aku", "makan", "minum", "tadi", "pagi", "siang", "malam"]
    words = text.lower().split()

    # filter kata penting
    filtered = [w for w in words if w not in stopwords]

    text_clean = " ".join(filtered)

    items = re.split(r",|dan", text_clean)

    for item in items:
        item = item.strip()

        # ambil qty
        qty_match = re.search(r"(\d+)", item)
        qty = int(qty_match.group(1)) if qty_match else 1

        clean_item = re.sub(r"\d+", "", item).strip()

        # ✅ EXACT MATCH
        if clean_item in food_list:
            detected.append((clean_item, qty))
            continue

        # ✅ FUZZY (backup)
        match = process.extractOne(
            clean_item,
            food_list,
            scorer=fuzz.token_sort_ratio
        )

        if match and match[1] > 85:
            detected.append((match[0], qty))

    return detected

# ================= RESPONSE =================
def nutribuddy_response(text):
    detected = extract_foods(text, df["nama"].tolist())

    if len(detected) == 0:
        return "Aku belum nemu makanan itu 😢 coba tulis lebih sederhana ya!"

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

    st.dataframe(
        result[["nama","qty","kalori","protein","lemak","karbohidrat"]],
        use_container_width=True
    )

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

    if total_lemak > 40:
        response += "\n⚠️ Lemak tinggi, coba pilih makanan rebus ya!"
    elif total_karbo > 80:
        response += "\n⚠️ Karbo tinggi, tambahin protein!"
    else:
        response += "\n✅ Asupan kamu cukup seimbang!"

    return response

# ================= RUN =================
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    reply = nutribuddy_response(prompt.lower())

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.chat_message("assistant").write(reply)
