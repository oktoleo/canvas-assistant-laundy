import streamlit as st
import google.generativeai as genai
from serpapi import GoogleSearch
import time
import re

# ==========================================
# 🔐 PENGATURAN KEAMANAN (PASSWORD)
# ==========================================
# User harus memasukkan kode ini untuk jadi PRO
KODE_RAHASIA = "oktoleo123" 
# ==========================================

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="LaundryCanvass AI",
    page_icon="🧼",
    layout="centered"
)

# --- 2. CSS HACK (UI BERSIH) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stDeployButton {display:none;}
            [data-testid="stToolbar"] {visibility: hidden !important;}
            .streamlit-expanderHeader {font-size: 14px; font-weight: bold; color: #2196F3;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. SIDEBAR LOGIN (PENENTU STATUS) ---
with st.sidebar:
    st.header("🔐 Akses Member")
    input_kode = st.text_input("Masukkan Kode Akses:", type="password")
    
    if input_kode == KODE_RAHASIA:
        st.success("✅ Mode PRO Aktif")
        STATUS_SUBSCRIPTION = "PRO"
    else:
        st.info("Mode Demo (Gratis)")
        STATUS_SUBSCRIPTION = "GRATIS"
        st.caption("Masukkan kode untuk membuka fitur Hidden Gem.")

# --- 4. SETUP API KEYS ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    if "SERPAPI_KEY" not in st.secrets:
        st.warning("⚠️ Kunci API belum dipasang.")
except:
    pass

# --- 5. SESSION STATE ---
if 'data_cache' not in st.session_state:
    st.session_state.data_cache = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'analysed_batches' not in st.session_state:
    st.session_state.analysed_batches = {}

# --- 6. FUNGSI LOGIKA ---

def cari_google_maps(lokasi):
    api_key = st.secrets.get("SERPAPI_KEY", "")
    if not api_key: return []
    try:
        params = {
          "engine": "google_maps", "q": f"Laundry di {lokasi}",
          "type": "search", "api_key": api_key, "hl": "id"
        }
        search = GoogleSearch(params)
        return search.get_dict().get("local_results", [])
    except:
        return []

def analisa_borongan_silent(data_batch, status):
    batch_id = f"{data_batch[0].get('title')}-{len(data_batch)}"
    if batch_id in st.session_state.analysed_batches:
        # Cek apakah status berubah? (Misal dari Gratis login ke Pro)
        # Kalau sebelumnya Gratis dan sekarang Pro, kita harus re-analisa bagian BLOCKED
        # Tapi untuk simpelnya, kita return cache dulu.
        return st.session_state.analysed_batches[batch_id]

    prompt_text = "Role: Sales Sabun.\nTugas: Analisa laundry berikut.\nDATA:\n"
    for i, item in enumerate(data_batch):
        nama = item.get("title", "No Name")
        alamat = item.get("address", "-")
        prompt_text += f"ID_{i}: {nama} | {alamat}\n"
    
    prompt_text += """
    INSTRUKSI:
    1. KODE: "GANG" (jika jalan kecil/perumahan) atau "RAYA" (jalan besar).
    2. SCRIPT: Chat WA pendek (max 1 kalimat) jualan sabun.
    Format Jawab: ID_0 | [KODE] | [SCRIPT]
    """

    candidates = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-pro']
    response_text = ""
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt_text)
            response_text = response.text
            if response_text: break 
        except:
            continue 

    hasil = {}
    if response_text:
        for line in response_text.split('\n'):
            if "|" in line:
                try:
                    parts = line.split("|")
                    id_match = re.search(r'\d+', parts[0])
                    if id_match and len(parts) >= 3:
                        idx = int(id_match.group())
                        kode = parts[1].strip().upper()
                        script = parts[2].strip()
                        
                        is_hidden = "GANG" in kode
                        # Logic Status dipindah ke Render agar dinamis saat login
                        hasil[idx] = {"hidden": is_hidden, "script": script}
                except:
                    continue
    
    st.session_state.analysed_batches[batch_id] = hasil
    return hasil

# --- 7. TAMPILAN UTAMA ---

st.title("🧼 Laundry Canvas Assitant")
st.markdown("""
<div style="margin-top: -15px; margin-bottom: 20px;">
    <b>Aplikasi Sales Intelijen Berbasis AI</b><br>
    <span style="font-size: 14px; color: #555;">Secepat kilat mencari prospek baru dengan menarik data realtime dari Google Maps ⚡</span>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])
with col1:
    lokasi_input = st.text_input("Area Target", placeholder="Ketik Nama Kecamatan...", label_visibility="collapsed")
with col2:
    tombol_scan = st.button("🚀 SCAN", use_container_width=True)

if tombol_scan:
    if not lokasi_input:
        st.warning("Mohon isi lokasi dulu.")
    else:
        with st.spinner(f"📡 Menghubungi satelit mencari laundry di {lokasi_input}..."):
            hasil_search = cari_google_maps(lokasi_input)
            if hasil_search:
                st.session_state.data_cache = hasil_search
                st.session_state.current_index = 0
                st.session_state.analysed_batches = {}
                st.success(f"Ditemukan {len(hasil_search)} Laundry!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Data tidak ditemukan.")

if st.session_state.data_cache:
    start = st.session_state.current_index
    end = start + 5
    batch = st.session_state.data_cache[start:end]
    
    if batch:
        st.write(f"Menampilkan data {start+1} - {min(end, len(st.session_state.data_cache))}")
        
        with st.spinner("🤖 AI sedang menganalisa profil bisnis..."):
            analisa = analisa_borongan_silent(batch, STATUS_SUBSCRIPTION)
        
        for i, item in enumerate(batch):
            script_cadangan = f"Halo kak {item.get('title')}, salam kenal. Boleh minta info laundry?"
            default_info = {"hidden": False, "script": script_cadangan}
            info = analisa.get(i, default_info)
            
            nama = item.get("title", "Laundry")
            alamat = item.get("address", "-")
            rating = item.get("rating", "")
            
            # LOGIKA KUNCI DISINI (DINAMIS BERDASARKAN LOGIN)
            is_blocked = False
            final_script = info['script']
            
            if STATUS_SUBSCRIPTION == "GRATIS" and info['hidden']:
                is_blocked = True
                final_script = "BLOCKED"

            if is_blocked:
                st.markdown(f"""
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 10px; border: 1px solid #ffeeba; margin-bottom: 10px;">
                    <div style="font-weight: bold; font-size: 18px;">🔒 {nama} <span style="font-size:14px">⭐{rating}</span></div>
                    <div style="color: #856404; font-weight: bold; margin-top: 5px;">⚠️ Calon Customer Detected</div>
                    <div style="font-size: 13px; color: #856404; margin-top: 5px;">
                        🔥 Lokasi Potensial (Gang/Perumahan):<br>✅ Bisnis Stabil & Customer Setia<br>✅ Minim Sewa Tempat
                    </div>
                    <div style="margin-top: 10px; font-weight: bold; color: #d39e00;">🔓 MASUKKAN KODE AKSES UNTUK BUKA</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                is_hidden = info['hidden']
                bg_color = "#e3f2fd" if is_hidden else "#ffffff"
                border_color = "#2196F3" if is_hidden else "#ddd"
                icon = "💎" if is_hidden else "🏠"
                
                st.markdown(f"""
                <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; border: 1px solid {border_color}; margin-bottom: 5px;">
                    <div style="font-weight: bold; font-size: 16px;">{start+i+1}. {icon} {nama} <span style="font-size:14px">⭐{rating}</span></div>
                    <div style="font-size: 12px; color: #666; margin-bottom: 10px;">📍 {alamat}</div>
                    <div style="background: #fff; padding: 8px; border: 1px dashed #999; font-family: monospace; font-size: 13px;">
                        {final_script}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                copy_content = f"🏢 *{nama}*\n📍 {alamat}\n\n💬 *Script WA:*\n{final_script}"
                with st.expander("📋 Klik Untuk Salin Data Lengkap"):
                    st.code(copy_content, language="markdown")

    st.markdown("---")
    col_prev, col_reset, col_next = st.columns([1, 1, 1])
    with col_prev:
        if start > 0:
            if st.button("⬅️ Back"):
                st.session_state.current_index -= 5
                st.rerun()
    with col_reset:
        if st.button("🔄 Reset"):
            st.session_state.data_cache = []; st.session_state.current_index = 0; st.session_state.analysed_batches = {}; st.rerun()
    with col_next:
        if end < len(st.session_state.data_cache):
            if st.button("Next ➡️"):
                st.session_state.current_index += 5; st.rerun()
