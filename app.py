import streamlit as st
import pandas as pd
from rapidfuzz import process
from collections import Counter
import re
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch

@st.cache_resource
def load_ner_model():
    model_path = "model"  # folder di repo kamu
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForTokenClassification.from_pretrained(model_path)
    return tokenizer, model

tokenizer, model = load_ner_model()

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

    /* Memastikan tombol pilihan punya jarak yang bagus */
    .option-btn-container {
        margin-bottom: 8px;
    }

    div.stButton > button { 
        background: white; 
        border: 1px solid rgba(139, 92, 246, 0.15); 
        border-radius: 20px; 
        padding: 10px 20px; 
        color: #4c1d95;
        transition: all 0.25s ease;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    div.stButton > button:hover { 
        border-color: #8b5cf6;
        background: #fdfaff;
        transform: translateY(-2px);
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
    path = "nutrition.csv"
    try:
        df = pd.read_csv(path)
        df.columns = df.columns.str.lower()
        df = df.rename(columns={"name": "nama", "calories": "kalori", "proteins": "protein", "fat": "lemak", "carbohydrate": "karbohidrat"})
        df["nama"] = df["nama"].str.lower()
        return df
    except: return pd.DataFrame()

df = load_data()
def preprocess_text(text):
    # Menghapus karakter khusus (simbol) sesuai poin jurnal
    text = re.sub(r'[^\w\s\d]', '', text) 
    # Mengubah ke huruf kecil
    text = text.lower().strip()
    return text
# --- 4. LOGIKA PINTAR ---
def get_nutrition_response(food_name, porsi=1.0):
    try:
        # Mengambil data dari dataframe
        data = df[df["nama"] == food_name].iloc[0]
        
        # Logika sistem mengalikan kuantitas (Sesuai Poin 4 Jurnal)
        kalori = data['kalori'] * porsi
        protein = data['protein'] * porsi
        lemak = data['lemak'] * porsi
        karbo = data['karbohidrat'] * porsi
        
        st.session_state.total_kalori_harian += kalori
        # Simpan riwayat dengan info porsi
        st.session_state.daftar_makan_harian.append(f"{food_name.title()} ({porsi}x)")
        
        return (
            f"✅ **NER & Fuzzy Match Berhasil!**\n\n"
            f"Item: **{food_name.title()}**\n"
            f"Jumlah: **{porsi} Porsi**\n"
            f"Total Energi: **{kalori:.1f} kkal**\n\n"
            f"**Rincian Gizi:**\n"
            f"Karbo: {karbo:.1f}g | Protein: {protein:.1f}g | Lemak: {lemak:.1f}g\n"
            f"--- \n"
            f"⚠️ _Catatan: Dihitung berdasarkan standar 100g per porsi._")
    except Exception as e:
        return f"Gagal menghitung nutrisi: {e}"
def process_input(text):
    text = text.lower()
    
    # 1. Fitur Ringkasan (Tetap sama)
    if any(k in text for k in ["total", "jumlah", "kurang", "sisa"]):
        total = st.session_state.total_kalori_harian
        if not st.session_state.daftar_makan_harian:
            return "Kamu belum makan apa-apa hari ini.", None
        ringkasan = ", ".join(st.session_state.daftar_makan_harian)
        return f"Total asupanmu: **{total:.0f} kkal**.\n\n**Riwayat:** {ringkasan}.", None

    # 2. Tahap NER (Simulasi IndoBERT untuk Food & Quantity)
    # Mencari angka (Quantity)
    nums = re.findall(r'\d+', text)
    qty = float(nums[0]) if nums else 1.0
    
    # Mencari nama makanan (Food) - Menghapus angka dan kata keterangan
    clean_query = re.sub(r'\d+', '', text)
    clean_query = clean_query.replace("makan", "").replace("habis", "").replace("tadi", "").strip()

    # 3. Tahap Integrasi Fuzzy Matching (Levenshtein Distance)
    food_list = df["nama"].tolist()
    matches = process.extract(clean_query, food_list, limit=3)
    
    # Ambil yang skornya di atas 75
    high_matches = [m[0] for m in matches if m[1] > 75]
    
    if not high_matches:
        return "Duh, aku ngga nemu makanan itu. Coba sebut yang lain ya!", None
    
    # Jika sangat akurat (>90), langsung tampilkan hasil
    if matches[0][1] > 90:
        return get_nutrition_response(matches[0][0], porsi=qty), None
    
    # Jika ambigu, berikan pilihan (Simpan qty ke session agar tidak hilang)
    st.session_state.last_qty = qty
    return "Maksud kamu yang mana nih? Pilih salah satu ya!", high_matches

    # PANGGIL LOGIKA NER (Sesuai Metodologi Jurnal)
    food_query, qty = extract_entities(text)

    if not food_query:
        return "Aku belum ngerti makanan yang kamu maksud 😢", None

    food_list = df["nama"].tolist()
    # TAHAP FUZZY MATCHING (Levenshtein Distance)
    matches = process.extract(food_query, food_list, limit=3)
    
    high_matches = [m[0] for m in matches if m[1] > 75]
    
    if not high_matches:
        return "Duh, aku ngga nemu makanan itu di database.", None

    if matches[0][1] > 90:
        # TAHAP KALKULASI (Multiplikasi Nilai Nutrisi)
        return get_nutrition_response(matches[0][0], porsi=qty), None
    
    st.session_state.last_qty = qty # Simpan porsi untuk pilihan tombol
    return "Maksud kamu yang mana nih?", high_matches
    
def extract_entities(text):
    # --- 1. PRE-PROCESSING (Sesuai Jurnal: Eliminasi Karakter Khusus) ---
    # Menghapus simbol seperti @, #, !, dll agar tidak mengganggu sistem
    text = re.sub(r'[^\w\s\d]', '', text) 
    text = text.lower().strip()

    # --- 2. NER QUANTITY (Ekstraksi Angka) ---
    # Mengambil angka dari kalimat untuk dikalikan ke nutrisi nanti
    nums = re.findall(r'\d+', text)
    qty = float(nums[0]) if nums else 1.0
    
    # --- 3. NER FOOD (Ekstraksi Nama Makanan) ---
    # Menghapus angka dan kata umum agar hanya menyisakan nama makanan
    clean_query = re.sub(r'\d+', '', text)
    stopwords = ["habis", "makan", "dan", "saya", "tadi", "sama", "dengan", "porsi", "aku"]
    
    # Memfilter kata-kata
    query_words = [w for w in clean_query.split() if w not in stopwords]
    final_food_query = " ".join(query_words)
    
    return final_food_query, qty
    
# --- 5. TAMPILAN UTAMA ---
main_container = st.container()

with main_container:
    if not st.session_state.messages:
        st.markdown("<div class='hero-text'>Hello!</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtext'>Sudah makan apa aja hari ini?</div>", unsafe_allow_html=True)
        
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

# Render Pilihan Fuzzy (VERSI RAPI & KONSISTEN)
    if st.session_state.pending_options:
        st.markdown("<div style='color: #4c1d95; font-weight: 600; margin: 20px 0 10px 0;'>Pilih salah satu ya:</div>", unsafe_allow_html=True)
        
        # Container utama dengan Flexbox agar tombol bisa menyamping dan otomatis turun baris
        st.markdown('<div style="display: flex; flex-wrap: wrap; gap: 12px; justify-content: flex-start;">', unsafe_allow_html=True)
        
        for i, opt in enumerate(st.session_state.pending_options):
            # Membuat container kecil untuk setiap tombol agar ukurannya konsisten
            with st.container():
                if st.button(opt.title(), key=f"choice_{i}"):
                    st.session_state.messages.append({"role": "user", "content": opt.title()})
    
                    # Ambil quantity yang tadi disimpan di session state
                    saved_qty = st.session_state.get('last_qty', 1.0)
                    
                    jawaban_final = get_nutrition_response(opt, porsi=saved_qty)
                    st.session_state.messages.append({"role": "assistant", "content": jawaban_final})
                    
                    st.session_state.pending_options = None
                    st.rerun()
                    
        st.markdown('</div>', unsafe_allow_html=True)

prompt = st.chat_input("Tanya NutriBuddy...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    jawaban, options = process_input(prompt)
    st.session_state.messages.append({"role": "assistant", "content": jawaban})
    st.session_state.pending_options = options
    st.rerun()
