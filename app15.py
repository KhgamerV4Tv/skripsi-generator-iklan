import os
import streamlit as st
import re
import io
import base64
import requests
import openai
import pandas as pd
import json # Ditambahkan untuk memproses string JSON rahasia
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
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
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
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
    
    .cost-badge { 
        background: #fee2e2; border-radius: 6px; padding: 0.4rem 0.8rem; 
        font-size: 0.8rem; color: #991b1b; display: inline-block; 
        font-weight: 600; margin-bottom: 0.8rem; border: 1px solid #fca5a5;
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
# DATA MASTER PROMPT & DATA KBLI UMKM
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
    "96012 - Jasa Penatu/Laundry": {"desc": "Usaha jasa pencucian pakaian.", "tipe": "jasa"}
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
# FUNGSI PENANGANAN KREDENSIAL GCP SEKURITI TINGGI (FIX SAKTI ERROR SECRETS)
# ==============================================================================
def load_gcp_credentials():
    from google.oauth2.service_account import Credentials
    # Opsi Cadangan Utama: Membaca string teks JSON murni (Sangat direkomendasikan karena kebal error TOML)
    if "GCP_SERVICE_ACCOUNT_JSON" in st.secrets:
        try:
            info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
            return Credentials.from_service_account_info(info), info["project_id"]
        except Exception as e:
            st.error(f"Gagal memproses GCP_SERVICE_ACCOUNT_JSON: {e}")
            
    # Opsi Cadangan Kedua: Membaca format blok kamus TOML bawaan Streamlit biasa
    if "GCP_SERVICE_ACCOUNT" in st.secrets:
        try:
            info = dict(st.secrets["GCP_SERVICE_ACCOUNT"])
            return Credentials.from_service_account_info(info), info["project_id"]
        except Exception as e:
            st.error(f"Gagal memproses GCP_SERVICE_ACCOUNT TOML: {e}")
            
    return None, None

# Fungsi inisialisasi client Firestore
def get_firestore_client():
    try:
        from google.cloud import firestore
        creds, project_id = load_gcp_credentials()
        if creds and project_id:
            return firestore.Client(project=project_id, credentials=creds)
        return None
    except Exception as e:
        st.error(f"Gagal koneksi Firestore: {e}")
        return None

# ==============================================================================
# ENGINE GENERATOR TEKS MURNI GOOGLE GEMINI SDK
# ==============================================================================
class GeminiStudioWrapper:
    def __init__(self, model_name, temperature):
        self.model_name = model_name
        self.temperature = temperature

    def invoke(self, messages):
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            generation_config = genai.types.GenerationConfig(temperature=self.temperature)
            model = genai.GenerativeModel(self.model_name, generation_config=generation_config)
            
            contents = []
            msg = messages[0] if isinstance(messages, list) else messages
            
            if hasattr(msg, 'content') and isinstance(msg.content, list):
                for part in msg.content:
                    if part.get("type") == "text": contents.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        b64_data = part["image_url"]["url"].split(",")[1]
                        img = Image.open(io.BytesIO(base64.b64decode(b64_data)))
                        contents.append(img)
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
llm_evaluator = GeminiStudioWrapper(model_name="gemini-2.5-pro", temperature=0.1)

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
        produk_block = f"\n  - Nama Produk/Menu: {nama_produk_global}\n  - Estimasi Harga Utama: Rp {harga_global:,}{promo_text}\n  - Catatan: Promo ini berlaku pukul rata untuk seluruh komoditas produk tersebut."
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
Jangan membuat gambar abstrak atau patung 3D geometris! Ide Visual harus berupa konsep fotografi komersial (Commercial Product Photography) nyata yang menampilkan wujud asli hidangan/produk '{brand_name}' secara lezat, menggugah selera, rapi, dan siap saji/pakai sesuai dengan suasana latar belakang yang dipilih.
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
def evaluate_ad_quality(brand_name, platform, generated_ad):
    prompt = f"Evaluasi iklan {brand_name} untuk {platform}. Berikan skor /100 untuk Relevansi, Target, dan Copywriting. Tampilkan di dalam tabel format Markdown.\n\nIKLAN:\n{generated_ad}"
    class DummyMsg:
        def __init__(self, content): self.content = content
    return llm_evaluator.invoke([DummyMsg(prompt)]).content

# ==============================================================================
# MODEL GENERATOR VISUAL DENGAN PROMPT ANCHORING (FIX KONEKSI SINKRONISASI)
# ==============================================================================
@st.cache_data(show_spinner=False)
def generate_imagen_image(prompt_text):
    if not prompt_text: return None
    try:
        from vertexai.vision_models import ImageGenerationModel
        import vertexai
        creds, project_id = load_gcp_credentials()
        if not creds or not project_id:
            st.error("Secrets GCP Kredensial tidak terdeteksi oleh aplikasi!")
            return None
            
        vertexai.init(project=project_id, location="us-central1", credentials=creds)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
        
        context_anchor = f"Commercial product photography for brand '{st.session_state.get('brand_name', 'UMKM')}' with category {st.session_state.get('kategori', 'Product')}. Clean and realistic presentation, no abstract elements, no 3D sculptures, highly relevant to the food/item menu, "
        final_prompt = context_anchor + prompt_text
        
        response = model.generate_images(prompt=final_prompt, number_of_images=1, aspect_ratio="1:1")
        return response.images[0]._image_bytes
    except Exception as e:
        st.error(f"Imagen Error: {e}")
        return None

@st.cache_data(show_spinner=False)
def generate_dalle_image(prompt_text):
    if not prompt_text: return None
    try:
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        context_anchor = f"Commercial product advertisement photography for '{st.session_state.get('brand_name', 'UMKM')}' showing realistic products of {st.session_state.get('kategori', 'Product')}. Photorealistic, delicious look, appetizing style, no abstract 3D figures, no geometric sculptures, "
        final_prompt = (context_anchor + prompt_text)[:900]
        
        res = client.images.generate(model="gpt-image-2", prompt=final_prompt, size="1024x1024", n=1)
        if res.data[0].url: return requests.get(res.data[0].url).content
    except Exception as e:
        st.error(f"Gagal total menghubungi OpenAI (gpt-image-2): {e}")
        return None

@st.cache_data(show_spinner=False)
def generate_gemini_flash_image(prompt_text):
    if not prompt_text: return None
    context_anchor = f"Realistic commercial marketing photography for '{st.session_state.get('brand_name', 'UMKM')}' matching the promotional text. Clean setup, sharp focus on the real items, strictly no abstract shape or complex 3D statues, "
    final_prompt = (context_anchor + prompt_text)[:900]
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/nano-banana-2')
        res = model.generate_content(final_prompt)
        for cand in res.candidates:
            for part in cand.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data: return part.inline_data.data
    except Exception:
        try:
            from vertexai.vision_models import ImageGenerationModel
            import vertexai
            creds, project_id = load_gcp_credentials()
            if creds and project_id:
                vertexai.init(project=project_id, location="us-central1", credentials=creds)
            else:
                vertexai.init(project="careful-ensign-477104-p5", location="us-central1")
            model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")
            res_vertex = model.generate_images(prompt=final_prompt, number_of_images=1, aspect_ratio="1:1")
            return res_vertex.images[0]._image_bytes
        except Exception:
            return None

# ==============================================================================
# POST-PROCESSING
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
# USER INTERFACE LAYOUT (KOLOM KIRI & KANAN)
# ==============================================================================
for k in ['main_txt', 'vis_prompt', 'ai_review', 'last_p', 'img_mem']:
    if k not in st.session_state: st.session_state[k] = None
if st.session_state.img_mem is None: st.session_state.img_mem = {"A": None, "B": None, "C": None}

col_f, col_r = st.columns([1, 1.35], gap="large")

# --- KOLOM KIRI: INPUT DATA ---
with col_f:
    db = get_firestore_client()
    db_status = "✅ Database Cloud Firestore Terkoneksi" if db else "⚠️ Firestore Mode Lokal Aktif"
    st.markdown(f'<div class="master-prompt-badge">🧠 {db_status}</div>', unsafe_allow_html=True)

    st.markdown('<div class="step-label">📋 Langkah 1: Identitas & Branding UMKM</div>', unsafe_allow_html=True)
    with st.container(border=True):
        col_l1, col_l2 = st.columns([1.3, 1])
        with col_l1: logo_file = st.file_uploader("Upload Logo", type=['png', 'jpg'])
        with col_l2: posisi_logo = st.selectbox("Posisi Logo", ["Kanan Atas", "Kiri Atas", "Kanan Bawah", "Kiri Bawah"])
        market = st.multiselect("Target Market", ["Umum", "Mahasiswa", "Pekerja Kantoran", "Ibu Rumah Tangga", "Anak Sekolah / Remaja"], default=["Umum"])

    st.markdown('<div class="step-label">📝 Langkah 2: Data Produk & Manajemen Harga</div>', unsafe_allow_html=True)
    with st.container(border=True):
        brand_name = st.text_input("Nama Brand / Usaha UMKM", placeholder="Rumah Pasila")
        st.session_state['brand_name'] = brand_name
        
        keywords_raw = st.text_input("Keywords USP Usaha", placeholder="tanpa pengawet, premium, isi tebal")
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        if keywords: st.markdown(" ".join([f'<span class="kw-tag">{k}</span>' for k in keywords]), unsafe_allow_html=True)
        
        kategori = st.selectbox("Kategori Usaha", list(KBLI_DATA.keys()))
        st.session_state['kategori'] = kategori
        st.markdown(f"<div class='kbli-desc'>📌 <b>Sektor:</b> {KBLI_DATA[kategori]['desc']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='elemen-box'><b>✅ Elemen Wajib Brosur:</b> {', '.join(get_elemen_wajib(kategori))}</div>", unsafe_allow_html=True)
        
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
                
                if st.button("➕ Tambah Item ke Daftar", use_container_width=True):
                    if item_nama:
                        st.session_state.daftar_produk_umkm.append({
                            "nama": item_nama,
                            "harga": item_harga,
                            "promo": item_promo
                        })
                        st.toast(f"{item_nama} ditambahkan!", icon="📝")
                    else:
                        st.warning("Nama item wajib diisi sebelum klik tambah.")

            if st.session_state.daftar_produk_umkm:
                st.markdown("**Daftar Item Terdaftar Saat Ini:**")
                df_curr_prod = pd.DataFrame(st.session_state.daftar_produk_umkm)
                st.dataframe(df_curr_prod, use_container_width=True)
                if st.button("🗑️ Kosongkan Daftar Item", type="secondary", use_container_width=True):
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
                with c2: foto_desc.append(st.text_input(f"Desc Foto {i+1}", key=f"f_{i}", label_visibility="collapsed", placeholder="Contoh: Kemasan kotak"))

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
        elif mode_promo == "Diskon Berbeda Per Item (Input Satu-Satu)" and not st.session_state.daftar_produk_umkm:
            st.warning("Daftar item produk kosong! Tambahkan minimal 1 item produk atau pilih mode Diskon Global.")
        else:
            st.session_state.img_mem = {"A": None, "B": None, "C": None}
            st.session_state.ai_review = None
            with st.spinner("AI sedang meracik copywriting..."):
                img_bytes = [f.getvalue() for f in foto_produk] if foto_produk else []
                res = generate_ad_text_master(
                    kategori, brand_name, keywords, gaya, platform, market, mood, bg, subjek, img_bytes, 
                    get_elemen_wajib(kategori), mode_promo, nama_produk_global, harga_global, promo_global, 
                    st.session_state.daftar_produk_umkm, foto_desc
                )
                vis, txt = parse_output_for_image(res)
                st.session_state.main_txt, st.session_state.vis_prompt = txt, vis
                st.session_state.last_p = {"nama": brand_name, "plat": platform}

# --- KOLOM KANAN: OUTPUT & FORM REVISI FIRESTORE PANDAS ---
with col_r:
    st.markdown('<div class="step-label">📱 Langkah 4: Copywriting & Evaluasi</div>', unsafe_allow_html=True)
    if st.session_state.main_txt:
        with st.container(border=True):
            st.markdown(st.session_state.main_txt)
            
            if st.button("🤖 Langkah 6: Review by Expert", use_container_width=True):
                with st.spinner("Juri mengevaluasi..."):
                    p = st.session_state.last_p
                    st.session_state.ai_review = evaluate_ad_quality(p["nama"], p["plat"], st.session_state.main_txt)
        
        if st.session_state.ai_review:
            with st.container(border=True): st.info(st.session_state.ai_review)

        st.divider()
        st.markdown('<div class="step-label">🎨 Langkah 5: Render Visual (Komparasi Skripsi)</div>', unsafe_allow_html=True)
        vis_edit = st.text_area("Instruksi Prompt Visual", value=st.session_state.vis_prompt, height=80)
        
        t_imgn, t_dalle, t_gmn = st.tabs(["🖼️ Imagen 3.0", "🎨 GPT Image 2", "⚡ Gemini Flash"])
        
        with t_imgn:
            st.markdown('<div class="cost-badge">Estimasi Biaya API: ~$0.03</div>', unsafe_allow_html=True)
            if st.button("Render Imagen 3.0", key="btn_a", use_container_width=True):
                with st.spinner("Merender Imagen via API murni..."):
                    # FIX: Memanggil hanya dengan argument tunggal vis_edit
                    raw = generate_imagen_image(vis_edit)
                    st.session_state.img_mem["A"] = apply_dynamic_branding(raw, logo_file, posisi_logo) if raw else None
            if st.session_state.img_mem["A"]:
                st.image(st.session_state.img_mem["A"], caption="Model A: Imagen 3.0")

        with t_dalle:
            st.markdown('<div class="cost-badge">Estimasi Biaya API: ~$0.05</div>', unsafe_allow_html=True)
            if st.button("Render GPT/DALL-E", key="btn_b", use_container_width=True):
                with st.spinner("Merender via OpenAI..."):
                    raw = generate_dalle_image(vis_edit)
                    st.session_state.img_mem["B"] = apply_dynamic_branding(raw, logo_file, posisi_logo) if raw else None
            if st.session_state.img_mem["B"]:
                st.image(st.session_state.img_mem["B"], caption="Model B: GPT Image")

        with t_gmn:
            st.markdown('<div class="cost-badge">Estimasi Biaya API: Gratis</div>', unsafe_allow_html=True)
            if st.button("Render Nano Banana 2", key="btn_c", use_container_width=True):
                with st.spinner("Merender Gambar..."):
                    raw = generate_gemini_flash_image(vis_edit)
                    st.session_state.img_mem["C"] = apply_dynamic_branding(raw, logo_file, posisi_logo) if raw else None
            if st.session_state.img_mem["C"]:
                st.image(st.session_state.img_mem["C"], caption="Model C: Gemini Nano Banana")

        # ==============================================================================
        # 📊 FORM EVALUASI DATA REAL-TIME CLOUD (FIX INDEX ORDER_BY ERROR)
        # ==============================================================================
        st.divider()
        st.markdown('<div class="step-label">📊 Form Pendataan Hasil Evaluasi Cloud</div>', unsafe_allow_html=True)
        st.caption("Data di bawah ini tersimpan permanen di Google Cloud Firestore (Aman meskipun web di-refresh).")
        
        with st.form("gform_mokap", clear_on_submit=True):
            f_bidang = st.selectbox("Pilih Bidang Hasil Pengujian", ["Bidang Food & Beverages", "Bidang Fashion/Pakaian", "Bidang Jasa & Retail"])
            f_tester = st.text_input("Nama Penilai / Tester", value="Dosen Pembimbing 2")
            f_catatan = st.text_area("Catatan atau Evaluasi Kualitatif Kinerja Model")
            f_skor = st.slider("Skor Kelayakan Hasil (1 - 100)", 1, 100, 85)
            
            submit_form = st.form_submit_button("📁 Simpan Data Permanen ke Google Cloud", use_container_width=True)
            
            if submit_form:
                new_entry = {
                    "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Bidang": f_bidang,
                    "Nama Usaha": brand_name if brand_name else "Tanpa Nama",
                    "Platform Target": platform,
                    "Tester": f_tester,
                    "Catatan Evaluasi": f_catatan,
                    "Skor Kelayakan": f_skor
                }
                if db:
                    try:
                        db.collection("evaluasi_skripsi").add(new_entry)
                        st.toast("Data evaluasi berhasil dikunci di Google Cloud Database!", icon="💾")
                    except Exception as e:
                        st.error(f"Gagal simpan ke Cloud: {e}")
                else:
                    st.session_state.skripsi_data.append(new_entry)
                    st.toast("Data disimpan sementara di mode lokal.", icon="💾")

        # Tarik data dari Cloud Firestore
        cloud_data = []
        if db:
            try:
                # FIX INDEX: Mengambil mentah tanpa order_by untuk menghindari Index Missing Error di GCP Console
                docs = db.collection("evaluasi_skripsi").stream()
                cloud_data = [doc.to_dict() for doc in docs]
            except Exception as e:
                st.warning(f"Gagal memuat data cloud langsung, menggunakan data lokal: {e}")
        
        # Gabungkan data untuk ditabelkan ke Pandas DataFrame
        final_log_list = cloud_data if db else st.session_state.skripsi_data

        if final_log_list:
            st.markdown("### 📋 Riwayat Log Data Terkumpul")
            df_log = pd.DataFrame(final_log_list)
            
            # FIX PANDAS SORTING: Pengurutan data terbaru dipindah ke sisi mesin lokal via Pandas
            if "Waktu" in df_log.columns:
                df_log = df_log.sort_values(by="Waktu", ascending=False).reset_index(drop=True)
                
            st.dataframe(df_log, use_container_width=True)
            
            csv_data = df_log.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Data Log Pengujian (.CSV)",
                data=csv_data,
                file_name="log_pengujian_skripsi_cloud.csv",
                mime="text/csv",
                use_container_width=True
            )

    else:
        st.info("👈 Silakan isi data di sebelah kiri lalu tekan Generate untuk memulai.")