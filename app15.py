import os
import streamlit as st
import re
import io
import base64
import requests
import openai
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from PIL import Image
import google.generativeai as genai

# ==============================================================================
# KONFIGURASI HALAMAN & CSS RESMI INAMIKRO (ELEGAN & MODERN)
# ==============================================================================
st.set_page_config(page_title="Inamikro Ad Generator V18 Pro", layout="wide", page_icon="📈")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600;700&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header { 
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 { color: #ffffff !important; font-size: 2.2rem; font-weight: 700; margin: 0; }
    .main-header p { color: #e2e8f0; margin-top: 0.5rem; font-size: 1rem; }
    
    .step-label { 
        font-weight: 700; font-size: 1.15rem; color: #1e40af; 
        margin: 1.5rem 0 0.8rem 0; padding-bottom: 0.3rem; border-bottom: 2px solid #e2e8f0;
    }
    
    div[data-testid="stVerticalBlockBorderWithFormatting"] {
        background-color: transparent; border: 1px solid #e2e8f0 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-radius: 12px !important; padding: 1.5rem !important;
    }
    
    .kbli-desc, .elemen-box, .photo-caption-box {
        border-radius: 8px; padding: 0.75rem 1rem; font-size: 0.85rem; 
        margin-top: 0.6rem; color: #1e293b !important; line-height: 1.5;
    }
    
    .kbli-desc { background: #eff6ff; border-left: 4px solid #3b82f6; }
    .elemen-box { background: #f0fdf4; border-left: 4px solid #22c55e; }
    .photo-caption-box { background: #fff7ed; border-left: 4px solid #f97316; margin-bottom: 0.8rem;}
    
    .kw-tag { 
        background: #e0f2fe; border-radius: 20px; padding: 6px 14px; 
        font-size: 0.8rem; color: #0369a1; margin: 4px 4px 10px 0; 
        display: inline-block; font-weight: 600; border: 1px solid #bae6fd;
    }
    .master-prompt-badge { 
        background: #f3e8ff; border-radius: 6px; padding: 0.4rem 0.8rem; 
        font-size: 0.8rem; color: #6b21a8; display: inline-block; 
        margin-bottom: 1rem; border: 1px solid #e9d5ff;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>📈 Inamikro Ad Generator V18 Pro</h1>
    <p>Platform Generator Copywriting & Komparasi Engine Visual Skripsi UMKM</p>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# DATA MASTER PROMPT & DATA KBLI UMKM (DIPERLUAS)
# ==============================================================================
MASTER_PROMPT_PATH = Path(__file__).parent / "master_prompt_inamikro.md"

@st.cache_data
def load_master_prompt():
    try:
        if MASTER_PROMPT_PATH.exists(): return MASTER_PROMPT_PATH.read_text(encoding="utf-8")
    except Exception: pass
    return "Kamu adalah Agen Marketing UMKM Pakar Copywriting Indonesia."

MASTER_PROMPT_FULL = load_master_prompt()

KBLI_DATA = {
    "56102 - Restoran dan Rumah Makan": {"desc": "Usaha yang menjual makanan siap saji di tempat makan.", "tipe": "food"},
    "56303 - Rumah Minum/Kafe": {"desc": "Usaha yang menjual minuman dan makanan ringan.", "tipe": "food"},
    "10794 - Industri Keripik & Makanan Ringan": {"desc": "Usaha produksi makanan ringan dalam kemasan.", "tipe": "food"},
    "10750 - Industri Makanan Olahan (Frozen Food)": {"desc": "Usaha produksi makanan yang diproses dan dikemas.", "tipe": "food"},
    "47841 - Perdagangan Eceran Makanan Keliling": {"desc": "Usaha berjualan makanan dan minuman keliling.", "tipe": "food"},
    "47711 - Perdagangan Eceran Pakaian (Fashion)": {"desc": "Usaha penjualan pakaian jadi eceran.", "tipe": "fashion"},
    "47726 - Perdagangan Eceran Sepatu/Sandal": {"desc": "Usaha penjualan alas kaki eceran.", "tipe": "fashion"},
    "47721 - Perdagangan Eceran Kosmetik & Skincare": {"desc": "Usaha penjualan produk kecantikan, makeup, dan perawatan kulit.", "tipe": "fashion"},
    "32990 - Industri Kerajinan Tangan (Kriya/Aksesoris)": {"desc": "Usaha pembuatan kerajinan, aksesoris, atau souvenir.", "tipe": "fashion"},
    "96012 - Jasa Penatu/Laundry": {"desc": "Usaha jasa pencucian pakaian.", "tipe": "jasa"},
    "96020 - Jasa Salon & Perawatan Kecantikan": {"desc": "Usaha layanan pangkas rambut, kosmetik, dan salon.", "tipe": "jasa"}
}

BROSUR_ELEMEN = {
    "food": ["Nama Produk", "Harga", "Keunggulan/USP", "Promo/Diskon", "Call-to-Action", "Kontak/WhatsApp"],
    "fashion": ["Nama Brand", "Jenis Produk", "Ukuran Tersedia", "Harga", "Call-to-Action", "Kontak/WhatsApp"],
    "jasa": ["Nama Usaha", "Jenis Layanan", "Harga/Tarif", "Keunggulan", "Call-to-Action", "Kontak/WhatsApp"],
}

def get_elemen_wajib(kategori):
    tipe = KBLI_DATA.get(kategori, {}).get("tipe", "food")
    return BROSUR_ELEMEN.get(tipe, BROSUR_ELEMEN["food"])

BACKGROUND_OPTIONS = {
    "🍽️ Meja Kayu Estetik": "rustic wooden table with warm bokeh background",
    "⬛ Studio Gelap Elegan": "dark matte studio background with dramatic side lighting",
    "🌿 Alam Hijau Segar": "fresh green leaves natural outdoor background",
    "⬜ Studio Putih Bersih": "clean white studio background with soft shadows",
    "🌸 Pastel Aesthetic": "soft pastel pink and cream aesthetic background",
}

if "skripsi_data" not in st.session_state:
    st.session_state.skripsi_data = []
if "daftar_produk_umkm" not in st.session_state:
    st.session_state.daftar_produk_umkm = []

# ==============================================================================
# FUNGSI PENANGANAN KREDENSIAL GCP & FIRESTORE
# ==============================================================================
def load_gcp_credentials():
    from google.oauth2.service_account import Credentials
    secret_keys = st.secrets.keys()
    target_key = "gcp_service_account" if "gcp_service_account" in secret_keys else "GCP_SERVICE_ACCOUNT" if "GCP_SERVICE_ACCOUNT" in secret_keys else None
    if target_key:
        try:
            info = dict(st.secrets[target_key])
            return Credentials.from_service_account_info(info), info["project_id"]
        except Exception: pass
    return None, None

def get_firestore_client():
    try:
        from google.cloud import firestore
        creds, project_id = load_gcp_credentials()
        if creds and project_id: return firestore.Client(project=project_id, credentials=creds)
    except Exception: pass
    return None

# ==============================================================================
# ENGINE GENERATOR TEKS GEMINI SDK
# ==============================================================================
class GeminiStudioWrapper:
    def __init__(self, model_name, temperature):
        self.model_name = model_name
        self.temperature = temperature

    def invoke(self, messages):
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel(self.model_name, generation_config=genai.types.GenerationConfig(temperature=self.temperature))
            
            contents = []
            msg = messages[0] if isinstance(messages, list) else messages
            
            if hasattr(msg, 'content') and isinstance(msg.content, list):
                for part in msg.content:
                    if part.get("type") == "text": contents.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        b64_data = part["image_url"]["url"].split(",")[1]
                        contents.append(Image.open(io.BytesIO(base64.b64decode(b64_data))))
            else:
                contents.append(str(msg.content if hasattr(msg, 'content') else msg))

            response = model.generate_content(contents)
            class AIResponse:
                def __init__(self, text): self.content = text
            return AIResponse(response.text)
        except Exception as e:
            class ErrorResponse:
                def __init__(self): self.content = f"⚠️ Error API Teks: {str(e)}"
            return ErrorResponse()

llm_generator = GeminiStudioWrapper(model_name="gemini-2.5-pro", temperature=0.3)

# ==============================================================================
# PARSING & PROMPT BUILDING
# ==============================================================================
def parse_output_for_image(markdown_text):
    try:
        matches = list(re.finditer(r"\*\*Ide Visual:\*\*[\s]*(.*?)(?=\n\n|\Z)", markdown_text, re.IGNORECASE | re.DOTALL))
        if matches:
            last_match = matches[-1]
            clean_idea = last_match.group(1).strip().replace('*', '').replace('\n', ' ')
            main_text = markdown_text[:last_match.start()].strip()
            return clean_idea[:500], main_text
    except Exception: pass
    return "", markdown_text

def build_context_block(kategori, brand_name, keywords_list, gaya, platform, market, mood, background, subjek, elemen_wajib, mode_promo, nama_produk_global, harga_global, promo_global, list_produk, photo_descriptions=None):
    market_str = ", ".join(market) if market else "Umum"
    keywords_str = ", ".join(keywords_list) if keywords_list else brand_name
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])
    bg_desc = BACKGROUND_OPTIONS.get(background, background)

    produk_block = ""
    if mode_promo == "Diskon Sama untuk Semua (Global)":
        promo_text = f" (Diberikan Promo Global: {promo_global})" if promo_global else " (Tanpa Promo)"
        produk_block = f"\n  - Nama Produk: {nama_produk_global}\n  - Harga: Rp {harga_global:,}{promo_text}"
    else:
        for idx, p in enumerate(list_produk):
            p_promo = f" (Promo: {p['promo']})" if p['promo'] else " (Tanpa Promo)"
            produk_block += f"\n  {idx+1}. {p['nama']} -> Harga: Rp {p['harga']:,}{p_promo}"

    photo_block = ""
    if photo_descriptions:
        photo_lines = [f"  - Foto {i+1}: {d.strip() or '(tanpa keterangan)'}" for i, d in enumerate(photo_descriptions)]
        photo_block = "\nKETERANGAN FOTO REFERENSI:\n" + "\n".join(photo_lines)

    return f"""
=== INPUT TERSTRUKTUR ===
- Nama Brand/Usaha: {brand_name}
- Karakteristik/USP Sektor: {keywords_str}
- Kategori Usaha: {kategori}
- Strategi Penawaran Produk:{produk_block}
- Target Market: {market_str} {photo_block}
- Platform Media: {platform} (Tone Copywriting: {gaya})
- Konsep Visual: {subjek} di {bg_desc} ({mood} atmosphere)
- Elemen Wajib yang HARUS Ditulis di dalam Iklan:
{elemen_str}

=== PERINTAH TEGAS GENERASI VISUAL ===
Jangan membuat gambar abstrak atau patung 3D geometris! Ide Visual harus berupa konsep fotografi komersial (Commercial Product Photography) nyata yang menampilkan wujud asli produk '{brand_name}' secara lezat/menarik, rapi, dan sesuai dengan suasana latar belakang yang dipilih.
"""

@st.cache_data(show_spinner=False)
def generate_ad_text_master(kategori, brand_name, keywords_list, gaya, platform, market, mood, background, subjek, images_bytes_list, elemen_wajib, mode_promo, nama_produk_global, harga_global, promo_global, list_produk, photo_descriptions=None):
    context = build_context_block(kategori, brand_name, keywords_list, gaya, platform, market, mood, background, subjek, elemen_wajib, mode_promo, nama_produk_global, harga_global, promo_global, list_produk, photo_descriptions)
    fidelity = "\n=== ATURAN VISUAL ===\nIde Visual HARUS mereplikasi BENTUK produk dari foto referensi persis.\n" if images_bytes_list else ""
    full_prompt = f"{MASTER_PROMPT_FULL}\n{context}\n{fidelity}\n=== TUGAS: Buat Teks Iklan {platform} ==="
    
    parts = [{"type": "text", "text": full_prompt}]
    for img_bytes in images_bytes_list:
        parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode('utf-8')}"}})
    
    class DummyMsg:
        def __init__(self, content): self.content = content
    return llm_generator.invoke([DummyMsg(parts)]).content

@st.cache_data(show_spinner=False)
def generate_ad_revision_master(main_txt, vis_prompt, revisi_input):
    old_output = f"{main_txt}\n\n**Ide Visual:**\n{vis_prompt}"
    prompt = f"""Kamu adalah Agen Pakar Marketing UMKM.
    
=== HASIL IKLAN SEBELUMNYA ===
{old_output}

=== INSTRUKSI REVISI DARI PENGGUNA ===
"{revisi_input}"

TUGAS:
Lakukan revisi HANYA pada bagian yang diminta. Jangan merombak total gaya bahasa yang sudah ada. 
Pastikan output akhir TETAP mengikuti format baku (ada Headline, Caption, Hashtags, dan bagian **Ide Visual:** di paling bawah untuk instruksi gambar).
"""
    class DummyMsg:
        def __init__(self, content): self.content = content
    return llm_generator.invoke([DummyMsg(prompt)]).content

@st.cache_data(show_spinner=False)
def evaluate_ad_quality_master(kategori, text_result):
    prompt = f"""Kamu adalah Dosen Pakar Marketing Digital & AI.
Tugasmu adalah menjadi 'LLM-as-a-Judge' untuk mengevaluasi naskah iklan UMKM berikut.

Kategori Usaha: {kategori}
Naskah Iklan:
{text_result}

Berikan penilaian analitis dan ketat. Tampilkan output HANYA dalam format ini:
SKOR KELAYAKAN: [Berikan angka 1-100]
ANALISIS PAKAR: [Berikan 2-3 kalimat penjelasan mengapa skor tersebut diberikan, sebutkan kelebihan dan kekurangannya berdasarkan target pasar]
"""
    class DummyMsg:
        def __init__(self, content): self.content = content
    return llm_generator.invoke([DummyMsg(prompt)]).content
# ==============================================================================
# MODEL GENERATOR OPENAI (GPT-IMAGE-2 / DALL-E)
# ==============================================================================
def generate_dalle_image(prompt_text):
    if not prompt_text: return None
    try:
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        context_anchor = f"Commercial product advertisement photography for '{st.session_state.get('brand_name', 'UMKM')}' showing realistic products of {st.session_state.get('kategori', 'Product')}. Photorealistic, high quality, appetizing style, no abstract 3D figures, no geometric sculptures, "
        safe_prompt = (context_anchor + prompt_text)[:900] 
        
        res = client.images.generate(model="gpt-image-2", prompt=safe_prompt, size="1024x1024", n=1)
        if hasattr(res.data[0], 'url') and res.data[0].url: 
            return requests.get(res.data[0].url).content
        if hasattr(res.data[0], 'b64_json') and res.data[0].b64_json: 
            return base64.b64decode(res.data[0].b64_json)
    except Exception as e:
        st.error(f"Gagal memproses GPT Image: {e}")
        return None

# ==============================================================================
# POST-PROCESSING WATERMARK
# ==============================================================================
def apply_dynamic_branding(main_bytes, logo_file, posisi):
    if not main_bytes or not logo_file: return main_bytes
    try:
        main_img = Image.open(io.BytesIO(main_bytes))
        logo_img = Image.open(logo_file).convert('RGBA')
        nw = int(main_img.width * 0.18)
        nh = int(nw * (logo_img.height / logo_img.width))
        logo_img = logo_img.resize((nw, nh), Image.Resampling.LANCZOS)
        
        pad = 28
        pos = (pad, pad)
        if "Kanan Atas" in posisi: pos = (main_img.width - nw - pad, pad)
        elif "Kanan Bawah" in posisi: pos = (main_img.width - nw - pad, main_img.height - nh - pad)
        elif "Kiri Bawah" in posisi: pos = (pad, main_img.height - nh - pad)

        res = main_img.copy()
        res.paste(logo_img, pos, logo_img)
        out = io.BytesIO()
        res.save(out, format='PNG')
        return out.getvalue()
    except Exception: return main_bytes

# ==============================================================================
# INITIALIZE SESSION STATE
# ==============================================================================
for k in ['main_txt', 'vis_prompt', 'last_p', 'img_mem', 'chat_history']:
    if k not in st.session_state: st.session_state[k] = None
if st.session_state.img_mem is None: st.session_state.img_mem = {"A": None}
if st.session_state.chat_history is None: st.session_state.chat_history = []

# ==============================================================================
# USER INTERFACE LAYOUT
# ==============================================================================
col_f, col_r = st.columns([1, 1.35], gap="large")

# --- KOLOM KIRI: INPUT DATA ---
with col_f:
    db = get_firestore_client()
    db_status = "✅ Database Cloud Terkoneksi" if db else "⚠️ Mode Lokal"
    st.markdown(f'<div class="master-prompt-badge">🧠 {db_status}</div>', unsafe_allow_html=True)

    st.markdown('<div class="step-label">📋 Langkah 1: Identitas & Branding UMKM</div>', unsafe_allow_html=True)
    with st.container(border=True):
        col_l1, col_l2 = st.columns([1.3, 1])
        with col_l1: logo_file = st.file_uploader("Upload Logo", type=['png', 'jpg'])
        with col_l2: posisi_logo = st.selectbox("Posisi Logo", ["Kanan Atas", "Kiri Atas", "Kanan Bawah", "Kiri Bawah"])
        market = st.multiselect("Target Market", ["Umum", "Mahasiswa", "Pekerja Kantoran", "Ibu Rumah Tangga", "Anak Sekolah / Remaja"], default=["Umum"])

    st.markdown('<div class="step-label">📝 Langkah 2: Data Produk & Manajemen Harga</div>', unsafe_allow_html=True)
    with st.container(border=True):
        brand_name = st.text_input("Nama Brand / Usaha UMKM", placeholder="Masukkan nama usaha Anda")
        st.session_state['brand_name'] = brand_name
        
        keywords_raw = st.text_input("Keywords USP Usaha", placeholder="tanpa pengawet, premium, isi tebal")
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        if keywords: st.markdown(" ".join([f'<span class="kw-tag">{k}</span>' for k in keywords]), unsafe_allow_html=True)
        
        kategori = st.selectbox("Kategori Usaha", list(KBLI_DATA.keys()))
        st.session_state['kategori'] = kategori
        st.markdown(f"<div class='kbli-desc'>📌 <b>Sektor:</b> {KBLI_DATA[kategori]['desc']}</div>", unsafe_allow_html=True)
        
        st.write("---")
        mode_promo = st.radio("Metode Penginputan Harga & Promo:", ["Diskon Sama untuk Semua (Global)", "Diskon Berbeda Per Item (Input Satu-Satu)"])
        
        nama_produk_global = ""
        harga_global = 0
        promo_global = ""

        if mode_promo == "Diskon Sama untuk Semua (Global)":
            st.markdown("##### 🌍 Input Harga & Promo Massal (Global)")
            nama_produk_global = st.text_input("Nama Menu / Kelompok Produk", placeholder="Siomay, Gyoza, dan Dimsum Goreng")
            c_g1, c_g2 = st.columns(2)
            with c_g1: harga_global = st.number_input("Estimasi Harga Mulai (Rp)", min_value=0, value=30000, step=1000)
            with c_g2: promo_global = st.text_input("Promo Massal", placeholder="Potongan 10rb porsi / Beli 2 Gratis 1")
        else:
            st.markdown("##### ➕ Input Item Manual Satu-per-Satu")
            with st.container():
                c_p1, c_p2, c_p3 = st.columns([1.5, 1.2, 1.3])
                with c_p1: item_nama = st.text_input("Nama Item", placeholder="Siomay", key="input_item_nama")
                with c_p2: item_harga = st.number_input("Harga Item (Rp)", min_value=0, value=15000, step=1000, key="input_item_harga")
                with c_p3: item_promo = st.text_input("Potongan/Promo", placeholder="Diskon 10rb", key="input_item_promo")
                
                if st.button("➕ Tambah Item", use_container_width=True):
                    if item_nama:
                        st.session_state.daftar_produk_umkm.append({"nama": item_nama, "harga": item_harga, "promo": item_promo})
                        st.toast(f"{item_nama} ditambahkan!", icon="📝")
            if st.session_state.daftar_produk_umkm:
                st.dataframe(pd.DataFrame(st.session_state.daftar_produk_umkm), use_container_width=True)
                if st.button("🗑️ Kosongkan Daftar Item", type="secondary"): 
                    st.session_state.daftar_produk_umkm = []
                    st.rerun()

        st.write("---")
        foto_produk = st.file_uploader("Upload Foto Referensi", type=['png', 'jpg'], accept_multiple_files=True)
        foto_desc = []
        if foto_produk:
            st.markdown('<div class="photo-caption-box">🏷️ <b>Beri keterangan singkat tiap foto</b></div>', unsafe_allow_html=True)
            for i, f in enumerate(foto_produk[:3]):
                c1, c2 = st.columns([1, 2.5])
                with c1: st.image(f, use_container_width=True)
                with c2: foto_desc.append(st.text_input(f"Desc Foto {i+1}", key=f"f_{i}", label_visibility="collapsed"))

    st.markdown('<div class="step-label">🎯 Langkah 3: Strategi Platform</div>', unsafe_allow_html=True)
    with st.container(border=True):
        platform = st.radio("Platform", ["Instagram", "WhatsApp", "TikTok"])
        cs1, cs2 = st.columns(2)
        with cs1: gaya = st.selectbox("Tone", ["Santai & Kekinian", "Profesional", "Hard-Selling"])
        with cs2: mood = st.selectbox("Mood", ["Cerah", "Gelap Elegan", "Hangat"])
        bg = st.selectbox("Background", list(BACKGROUND_OPTIONS.keys()))
        subjek = st.selectbox("Subjek", ["Produk saja", "1 Orang", "Keluarga"])

    if st.button("🚀 GENERATE IKLAN", type="primary", use_container_width=True):
        if not brand_name: 
            st.warning("Isi nama brand/usaha dulu!")
        else:
            st.session_state.img_mem = {"A": None}
            st.session_state.chat_history = [] # Reset riwayat chat untuk generate baru
            st.session_state.ai_eval_result = None # Reset hasil evaluasi lama
            
            with st.spinner("🤖 Agent 1: AI sedang meracik copywriting..."):
                img_bytes = [f.getvalue() for f in foto_produk] if foto_produk else []
                res = generate_ad_text_master(
                    kategori, brand_name, keywords, gaya, platform, market, mood, bg, subjek, img_bytes, 
                    get_elemen_wajib(kategori), mode_promo, nama_produk_global, harga_global, promo_global, 
                    st.session_state.daftar_produk_umkm, foto_desc
                )
                vis, txt = parse_output_for_image(res)
                st.session_state.main_txt, st.session_state.vis_prompt = txt, vis
                st.session_state.last_p = {"nama": brand_name, "plat": platform}
                
            # AGENT 2 OTOMATIS BERJALAN SETELAH AGENT 1 SELESAI
            with st.spinner("⚖️ Agent 2: Mengevaluasi kualitas (Quality Control)..."):
                hasil_evaluasi = evaluate_ad_quality_master(kategori, txt)
                st.session_state.ai_eval_result = hasil_evaluasi

# --- KOLOM KANAN: OUTPUT & REVISI ---
with col_r:
    st.markdown('<div class="step-label">📱 Langkah 4: Copywriting Hasil AI</div>', unsafe_allow_html=True)
    if st.session_state.main_txt:
        with st.container(border=True):
            # FITUR 2-WAY: Sakelar untuk mengubah mode tampilan
            edit_mode = st.toggle("✏️ Mode Edit Manual")
            
            if edit_mode:
                # Jika sakelar ON: Munculkan kotak ketik
                st.info("💡 Silakan ketik/edit teks di bawah ini. Matikan sakelar untuk melihat hasil rapinya kembali.")
                st.session_state.main_txt = st.text_area(
                    "Edit Teks Copywriting", 
                    value=st.session_state.main_txt, 
                    height=350, 
                    label_visibility="collapsed"
                )
            else:
                # Jika sakelar OFF: Tampilkan versi elegan (Markdown)
                st.markdown(st.session_state.main_txt)
            
            # --- FITUR UX: SERTIFIKAT LULUS QC DARI AI EVALUATOR ---
            if st.session_state.get('ai_eval_result'):
                st.divider()
                st.success("✅ **Lulus Uji Kualitas Pakar AI (Quality Control)**")
                with st.expander("📊 Lihat Detail Analisis (Opsional)"):
                    st.markdown(st.session_state.ai_eval_result)
            
        st.divider()
        st.markdown('<div class="step-label">🎨 Langkah 5: Render Visual Final</div>', unsafe_allow_html=True)
        
        with st.expander("⚙️ Lihat/Edit Instruksi AI (Opsional)"):
            st.session_state.vis_prompt = st.text_area(
                "Instruksi Prompt Visual", 
                value=st.session_state.vis_prompt, 
                height=80, 
                label_visibility="collapsed"
            )
        
        st.info("💡 Sistem menggunakan AI GPT Image 2 (Dioptimalkan untuk teks promo dan poster komersial).")
        if st.button("✨ Render Foto Studio (Otomatis)", type="primary", use_container_width=True):
            with st.spinner("📸 Sedang di studio AI... Merender gambar (sekitar 10 detik)..."):
                raw = generate_dalle_image(st.session_state.vis_prompt)
                st.session_state.img_mem["A"] = apply_dynamic_branding(raw, logo_file, posisi_logo) if raw else None
                
        if st.session_state.img_mem["A"]:
            st.success("✅ Gambar berhasil dibuat!")
            st.image(st.session_state.img_mem["A"], caption="Hasil Render Final Inamikro")
            st.download_button(
                label="⬇️ Download Gambar Resolusi Tinggi", 
                data=st.session_state.img_mem["A"], 
                file_name=f"promo_{brand_name.replace(' ', '_') if brand_name else 'umkm'}.png", 
                mime="image/png", 
                use_container_width=True
            )

        # =========================================================
        # 💬 LANGKAH 6: CHATBOT REVISI AI
        # =========================================================
        st.divider()
        st.markdown('<div class="step-label">💬 Langkah 6: Asisten Revisi AI (Otomatis)</div>', unsafe_allow_html=True)
        st.caption("Kurang pas? Ketik perintah di bawah (misal: 'Tambahkan nomor WA 08123', 'Tambahkan tulisan Buy 1 Get 1 di gambar').")
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        revisi_input = st.chat_input("Ketik instruksi revisi di sini...")
        if revisi_input:
            st.session_state.chat_history.append({"role": "user", "content": revisi_input})
            with st.spinner("🧠 AI sedang merevisi naskah & visual..."):
                new_raw = generate_ad_revision_master(st.session_state.main_txt, st.session_state.vis_prompt, revisi_input)
                new_vis, new_txt = parse_output_for_image(new_raw)
                
                st.session_state.main_txt = new_txt
                st.session_state.vis_prompt = new_vis
                st.session_state.img_mem["A"] = None # Reset gambar lama
                
                st.session_state.chat_history.append({"role": "assistant", "content": "✅ Revisi selesai! Hasil teks di **Langkah 4** dan instruksi gambar di **Langkah 5** sudah saya perbarui. Silakan Render Ulang gambarnya."})
                st.rerun()

        # ==============================================================================
        # 📊 ADMIN PANEL & FORM EVALUASI DOSEN (TERSEMBUNYI)
        # ==============================================================================
        st.divider()
        
        # Tarik data log dari Cloud (jika ada)
        cloud_data = []
        if db:
            try: cloud_data = [doc.to_dict() for doc in db.collection("evaluasi_skripsi").stream()]
            except Exception: pass
            
        final_log_list = cloud_data if db else st.session_state.skripsi_data
        
        # SEMBUNYIKAN SEMUANYA DI DALAM MENU LIPAT BER-PIN
        with st.expander("🔐 Menu Admin & Evaluasi Pakar (Khusus Penguji)"):
            admin_pin = st.text_input("Masukkan PIN Admin:", type="password")
            
            if admin_pin == "skripsiA":
                st.success("✅ Akses Admin Terbuka!")
                
                # --- 1. FORM EVALUASI (Hanya muncul jika PIN benar) ---
                st.markdown("### 📝 Form Penilaian UAT (Dosen/Pakar)")
                with st.form("gform_mokap", clear_on_submit=True):
                    f_bidang = st.selectbox("Bidang Hasil Pengujian", ["Bidang Food & Beverages", "Bidang Fashion", "Bidang Jasa"])
                    f_tester = st.text_input("Nama Penilai", value="Dosen Pembimbing")
                    f_catatan = st.text_area("Catatan Evaluasi")
                    f_skor = st.slider("Skor Kelayakan Hasil (1 - 100)", 1, 100, 85)
                    
                    if st.form_submit_button("📁 Simpan Data Pengujian", use_container_width=True):
                        new_entry = {"Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Bidang": f_bidang, "Nama Usaha": brand_name, "Platform Target": st.session_state.last_p["plat"] if st.session_state.last_p else "N/A", "Tester": f_tester, "Catatan Evaluasi": f_catatan, "Skor Kelayakan": f_skor}
                        if db:
                            try: 
                                db.collection("evaluasi_skripsi").add(new_entry)
                                st.toast("Tersimpan di Cloud!", icon="💾")
                            except Exception as e: st.error(f"Gagal: {e}")
                        else:
                            st.session_state.skripsi_data.append(new_entry)
                            st.toast("Tersimpan lokal.", icon="💾")
                
                st.divider()
                
                # --- 2. TABEL LOG DATABASE PENGUJIAN ---
                st.markdown("### 🗄️ Log Database Pengujian")
                if final_log_list:
                    df_log = pd.DataFrame(final_log_list)
                    if "Waktu" in df_log.columns: df_log = df_log.sort_values(by="Waktu", ascending=False).reset_index(drop=True)
                    st.dataframe(df_log, use_container_width=True)
                    st.download_button("📥 Download .CSV", data=df_log.to_csv(index=False).encode('utf-8'), file_name="log_skripsi.csv", mime="text/csv", use_container_width=True)
                else:
                    st.info("Belum ada data pengujian yang tersimpan.")
                    
            elif admin_pin: 
                st.error("⚠️ PIN Salah!")

    else:
        st.info("👈 Silakan isi data di sebelah kiri lalu tekan Generate untuk memulai.")