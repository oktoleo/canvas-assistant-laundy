import streamlit as st
import google.generativeai as genai
from serpapi import GoogleSearch
import time
import re

# ==========================================
# 🔐 PENGATURAN KEAMANAN
# ==========================================
KODE_RAHASIA = "CUAN2025" 
# ==========================================

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Laundry Sales Assistant",
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
            input.st-bd {border: 1px solid #aaa;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if 'data_cache' not in st.session_state:
    st.session_state.data_cache = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'analysed_batches' not in st.session_state:
    st.session_state.analysed_batches = {}
if 'user_status' not in st.session_state:
    st.session_state.user_status = "GRATIS" 

# --- 4. SETUP API KEYS ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    if "SERPAPI_KEY" not in st.secrets:
        st.warning("⚠️ Kunci API belum dipasang.")
except:
    pass

# --- 5. FUNGSI LOGIKA ---

def cari_google_maps(lokasi, limit):
    api_key = st.secrets.get("SERPAPI_KEY", "")
    if not api_key: return []
    try:
        params = {
          "engine": "google_maps", "q": f"Laundry di {lokasi}",
          "type": "search", "api_key": api_key, "hl": "id"
        }
        search = GoogleSearch(params)
        raw_results = search.get_dict().get("local_results", [])
        return raw_results[:limit]
    except:
        return []

def analisa_borongan_silent(data_batch, status):
    batch_id = f"{data_batch[0].get('title')}-{len(data_batch)}"
    if batch_id in st.session_state.analysed_batches:
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
                        hasil[idx] = {"hidden": is_hidden, "script": script}
                except:
                    continue
    st.session_state.analysed_batches[batch_id] = hasil
    return hasil

# --- 6. TAMPILAN UTAMA ---

st.title("🧼 ASA for Laundry")

# === LOGIN EXPANDER ===
if st.session_state.user_status == "GRATIS":
    with st.expander("🔐 Punya Kode Akses? Masuk Di Sini"):
        col_pass, col_btn = st.columns([3, 1])
        with col_pass:
            input_kode = st.text_input("Kode:", type="password", label_visibility="collapsed", placeholder="Masukkan Kode...")
        with col_btn:
            if st.button("Masuk"):
                if input_kode == KODE_RAHASIA:
                    st.session_state.user_status = "PRO"
                    st.success("Berhasil! Mode PRO Aktif.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Kode Salah!")

# === INFO BAR (FORMAT 2 BARIS) ===
if st.session_state.user_status == "PRO":
    LIMIT_DATA = 30
    INFO_RADIUS = "10 KM"
    # Menggunakan \n untuk pindah baris
    st.info(f"💎 **Status: MEMBER PRO**  \n📡 Radius: **{INFO_RADIUS}** (Max 30 Data)")
else:
    LIMIT_DATA = 10
    INFO_RADIUS = "1 KM"
    # Menggunakan \n untuk pindah baris
    st.warning(f"🔓 **Status: DEMO GRATIS**  \n📡 Radius: **{INFO_RADIUS}** (Max 10 Data)")
    st.caption("ℹ️ *Klik menu 'Punya Kode Akses' untuk radius lebih luas.*")

st.markdown("""
<div style="margin-top: 10px; margin-bottom: 20px;">
    <b>Cari Prospek Laundry Secepat Kilat</b>
    <span style="font-size: 14px; color: #555;"><br>Asisten AI akan mengambil data realtime Google Maps.</span>
    <span style="font-size: 14px; color: #555;"><br>Masukkan nama Kecamatan/Kelurahan target Anda.</span>
</div>
""", unsafe_allow_html=True)

# INPUT UI
lokasi_input = st.text_input("📍 Lokasi Target:", placeholder="Contoh: Tebet, Jakarta Selatan")
tombol_scan = st.button("🚀 SCAN SEKARANG", use_container_width=True, type="primary")

if tombol_scan:
    if not lokasi_input:
        st.error("⚠️ Mohon ketik lokasi dulu.")
    else:
        with st.spinner(f"📡 Scanning radius {INFO_RADIUS} ({LIMIT_DATA} Data) di area {lokasi_input}..."):
            hasil_search = cari_google_maps(lokasi_input, LIMIT_DATA)
            
            if hasil_search:
                st.session_state.data_cache = hasil_search
                st.session_state.current_index = 0
                st.session_state.analysed_batches = {}
                st.success(f"✅ Ditemukan {len(hasil_search)} Laundry")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Data tidak ditemukan. Coba nama lokasi lain.")

# RENDER DATA & PAGINATION
if st.session_state.data_cache:
    start = st.session_state.current_index
    end = start + 5 
    batch = st.session_state.data_cache[start:end]
    
    if batch:
        total_data = len(st.session_state.data_cache)
        st.write(f"Menampilkan urutan {start+1} - {min(end, total_data)} dari total {total_data} data")
        
        with st.spinner("🤖 AI sedang menganalisa profil bisnis..."):
            analisa = analisa_borongan_silent(batch, st.session_state.user_status)
        
        for i, item in enumerate(batch):
            script_cadangan = f"Halo kak {item.get('title')}, salam kenal. Boleh minta info laundry?"
            default_info = {"hidden": False, "script": script_cadangan}
            info = analisa.get(i, default_info)
            
            nama = item.get("title", "Laundry")
            alamat = item.get("address", "-")
            rating = item.get("rating", "")
            
            is_blocked = False
            final_script = info['script']
            
            if st.session_state.user_status == "GRATIS" and info['hidden']:
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
