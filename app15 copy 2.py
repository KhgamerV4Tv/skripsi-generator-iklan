import os
import streamlit as st
# # DEBUGGING: Cek apakah secrets terbaca
# if "GCP_SERVICE_ACCOUNT" not in st.secrets:
#     st.sidebar.error("Secrets BELUM TERBACA! Cek spelling di Dashboard.")
# else:
#     st.sidebar.success("Secrets Terbaca! Siap Render.")

# ==============================================================================
# CSS FIX UNTUK DARK MODE STREAMLIT (TEKS MENGHILANG)
# ==============================================================================
# st.markdown("""
#     <style>
#     /* Memaksa semua teks di dalam kotak Info (Biru), Success (Hijau), dan Warning/Error menjadi Hitam */
#     div[data-testid="stAlert"] p, 
#     div[data-testid="stAlert"] span, 
#     div[data-testid="stAlert"] div {
#         color: #000000 !important;
#         font-weight: 500 !important;
#     }
#     </style>
# """, unsafe_allow_html=True)

import re
import io
import base64
import requests
import openai
from pathlib import Path
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import google.generativeai as genai

# ==============================================================================
# KONFIGURASI HALAMAN & CSS RESMI INAMIKRO
# ==============================================================================
st.set_page_config(page_title="Inamikro Ad Generator V18 Final", layout="wide", page_icon="📈")

st.markdown("""
<style>
    .main-header { text-align: center; padding: 0.8rem 0 0.3rem 0; }
    .main-header h1 { color: #1565C0; font-size: 2rem; margin-bottom: 0.1rem; }
    .step-label { font-weight: 700; font-size: 1rem; color: #1565C0; margin: 0.8rem 0 0.3rem 0; }
    
    /* FIX WARNA TEKS DI SINI: Ditambah color hitam pekat agar tembus Dark Mode */
    .kbli-desc, .elemen-box, .photo-caption-box {
        border-radius: 4px; padding: 0.4rem 0.7rem; font-size: 0.81rem; margin-top: 0.3rem;
        color: #000000 !important; 
    }
    
    .kbli-desc { background: #f0f4ff; border-left: 3px solid #1565C0; }
    .elemen-box { background: #f7fff7; border-left: 3px solid #2e7d32; }
    .photo-caption-box { background: #fff3e0; border-left: 3px solid #fb8c00; margin-bottom: 0.5rem;}
    .kw-tag { background:#e3f2fd; border-radius:12px; padding:4px 12px; font-size:0.85rem; color:#1565C0; margin:4px 4px 10px 0; display:inline-block; font-weight: 500; border: 1px solid #bbdefb;}
    .cost-badge { background:#ffebee; border-radius:4px; padding:0.2rem 0.5rem; font-size:0.75rem; color:#c62828; display:inline-block; font-weight:bold; margin-bottom: 0.5rem;}
    .master-prompt-badge { background:#ede7f6; border-radius:4px; padding:0.3rem 0.6rem; font-size:0.78rem; color:#4527a0; display:inline-block; margin-bottom:0.5rem; }
</style>
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

# ==============================================================================
# ENGINE GENERATOR TEKS MURNI GOOGLE GEMINI SDK (ANTI-ERROR 503 METADATA)
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
                    if part.get("type") == "text":
                        contents.append(part.get("text", ""))
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

def build_context_block(kategori, nama_produk, keywords_list, gaya, platform, market, mood, background, subjek, elemen_wajib, photo_descriptions=None):
    market_str = ", ".join(market) if market else "Umum"
    keywords_str = ", ".join(keywords_list) if keywords_list else nama_produk
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])
    bg_desc = BACKGROUND_OPTIONS.get(background, background)

    photo_block = ""
    if photo_descriptions:
        photo_lines = [f"  - Foto {i+1}: {d.strip() or '(tanpa keterangan)'}" for i, d in enumerate(photo_descriptions)]
        photo_block = "\nKETERANGAN FOTO REFERENSI:\n" + "\n".join(photo_lines)

    return f"""
=== INPUT TERSTRUKTUR ===
- Produk: {nama_produk} ({keywords_str})
- Market: {market_str}
- Kategori: {kategori} {photo_block}
- Platform: {platform} (Tone: {gaya})
- Visual: {subjek} di {bg_desc} ({mood})
- Elemen Wajib:
{elemen_str}
"""

@st.cache_data(show_spinner=False)
def generate_ad_text_master(kategori, nama_produk, keywords_list, gaya, platform, market, mood, background, subjek, images_bytes_list, elemen_wajib, photo_descriptions=None):
    context = build_context_block(kategori, nama_produk, keywords_list, gaya, platform, market, mood, background, subjek, elemen_wajib, photo_descriptions)
    fidelity = "\n=== ATURAN VISUAL ===\nIde Visual HARUS mereplikasi BENTUK produk dari foto referensi persis.\n" if images_bytes_list else ""
    full_prompt = f"{MASTER_PROMPT_FULL}\n{context}\n{fidelity}\n=== TUGAS: Buat Teks Iklan {platform} ==="
    
    parts = [{"type": "text", "text": full_prompt}]
    for img_bytes in images_bytes_list:
        parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode('utf-8')}"}})
    
    class DummyMsg:
        def __init__(self, content): self.content = content
    return llm_generator.invoke([DummyMsg(parts)]).content

@st.cache_data(show_spinner=False)
def evaluate_ad_quality(nama_produk, platform, generated_ad):
    prompt = f"Evaluasi iklan {nama_produk} untuk {platform}. Berikan skor /100 untuk Relevansi, Target, dan Copywriting. Tampilkan di dalam tabel format Markdown.\n\nIKLAN:\n{generated_ad}"
    class DummyMsg:
        def __init__(self, content): self.content = content
    return llm_evaluator.invoke([DummyMsg(prompt)]).content

# ==============================================================================
# TIGA MODEL GENERATOR VISUAL UNTUK BAB 4 KOMPARASI SKRIPSI (ASLI 100%)
# ==============================================================================
@st.cache_data(show_spinner=False)
def generate_imagen_image(prompt_text):
    if not prompt_text: return None
    try:
        from vertexai.vision_models import ImageGenerationModel
        import vertexai
        from google.oauth2.service_account import Credentials
        
        # CEK APAKAH SECRETS TERBACA
        if "GCP_SERVICE_ACCOUNT" not in st.secrets:
            st.error("Secrets GCP_SERVICE_ACCOUNT tidak terdeteksi oleh aplikasi!")
            return None
            
        # KONVERSI SECRETS KE FORMAT GOOGLE CREDENTIALS
        secrets_dict = dict(st.secrets["GCP_SERVICE_ACCOUNT"])
        creds = Credentials.from_service_account_info(secrets_dict)
        
        # INISIALISASI
        vertexai.init(project="careful-ensign-477104-p5", location="us-central1", credentials=creds)

        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
        response = model.generate_images(prompt=f"professional product photography, {prompt_text}", number_of_images=1, aspect_ratio="1:1")
        return response.images[0]._image_bytes
    except Exception as e:
        st.error(f"Imagen Error: {e}")
        return None
@st.cache_data(show_spinner=False)
def generate_dalle_image(prompt_text):
    if not prompt_text: return None
    try:
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        safe_prompt = prompt_text[:900] 
        
        # MURNI HANYA MEMANGGIL gpt-image-2 SESUAI INSTRUKSI KEVIN
        res = client.images.generate(model="gpt-image-2", prompt=safe_prompt, size="1024x1024", n=1)
        if res.data[0].url: 
            return requests.get(res.data[0].url).content
        if hasattr(res.data[0], 'b64_json') and res.data[0].b64_json: 
            return base64.b64decode(res.data[0].b64_json)
            
    except Exception as e:
        st.error(f"Gagal total menghubungi OpenAI (gpt-image-2): {e}")
        return None

@st.cache_data(show_spinner=False)
def generate_gemini_flash_image(prompt_text):
    if not prompt_text: return None
    safe_prompt = prompt_text[:900]
    try:
        # Skenario Utama: Nano Banana 2
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/nano-banana-2')
        res = model.generate_content(safe_prompt)
        for cand in res.candidates:
            for part in cand.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    return part.inline_data.data
    except Exception as e:
        print(f"Nano Banana 2 AI Studio gagal, pindah ke Vertex AI... Error: {e}")
        
        # Skenario Fallback: Imagen Fast Generate 001
        try:
            from vertexai.vision_models import ImageGenerationModel
            import vertexai
            try:
                from google.oauth2.service_account import Credentials
                if "GCP_SERVICE_ACCOUNT" in st.secrets:
                    creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"])
                    vertexai.init(project="careful-ensign-477104-p5", location="us-central1", credentials=creds)
                else:
                    vertexai.init(project="careful-ensign-477104-p5", location="us-central1")
            except Exception:
                vertexai.init(project="careful-ensign-477104-p5", location="us-central1")

            model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")
            res_vertex = model.generate_images(prompt=safe_prompt, number_of_images=1, aspect_ratio="1:1")
            return res_vertex.images[0]._image_bytes
        except Exception as ex:
            st.error("Semua jalur Google AI (AI Studio & Vertex) buntu.")
            return None

# ==============================================================================
# POST-PROCESSING (LOGO & WATERMARK UMKM)
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
# USER INTERFACE STREAMLIT UTAMA (DILENGKAPI INDIKATOR BIAYA)
# ==============================================================================
col_b1, col_b2 = st.columns([3, 1])
with col_b1:
    mp_status = "✅ Master Prompt V1.0 Aktif" if MASTER_PROMPT_PATH.exists() else "⚠️ Master Prompt fallback"
    st.markdown(f'<div class="master-prompt-badge">🧠 {mp_status} | <code>master_prompt_inamikro.md</code></div>', unsafe_allow_html=True)

for k in ['main_txt', 'vis_prompt', 'ai_review', 'last_p', 'img_mem']:
    if k not in st.session_state: st.session_state[k] = None
if st.session_state.img_mem is None: st.session_state.img_mem = {"A": None, "B": None, "C": None}

col_f, col_r = st.columns([1, 1.45], gap="large")

with col_f:
    st.markdown('<div class="step-label">📋 Langkah 1: Identitas & Branding UMKM</div>', unsafe_allow_html=True)
    with st.container(border=True):
        col_l1, col_l2 = st.columns([1.3, 1])
        with col_l1: logo_file = st.file_uploader("Upload Logo", type=['png', 'jpg'])
        with col_l2: posisi_logo = st.selectbox("Posisi Logo", ["Kanan Atas", "Kiri Atas", "Kanan Bawah", "Kiri Bawah"])
        market = st.multiselect("Target Market", ["Umum", "Mahasiswa", "Pekerja Kantoran", "Ibu Rumah Tangga", "Anak Sekolah / Remaja"], default=["Umum"])

    st.markdown('<div class="step-label">📝 Langkah 2: Data Produk & Referensi Visual</div>', unsafe_allow_html=True)
    with st.container(border=True):
        nama_produk = st.text_input("Nama Produk", placeholder="Bakwan Sowan")
        keywords_raw = st.text_input("Keywords USP", placeholder="keju creamy, halal, harga terjangkau")
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        
        # --- UI TAGS USP HIGHLIGHT ---
        if keywords: st.markdown(" ".join([f'<span class="kw-tag">{k}</span>' for k in keywords]), unsafe_allow_html=True)
        
        kategori = st.selectbox("Kategori Usaha", list(KBLI_DATA.keys()))
        st.markdown(f"<div class='kbli-desc'>📌 <b>Sektor:</b> {KBLI_DATA[kategori]['desc']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='elemen-box'><b>✅ Elemen Wajib Brosur:</b> {', '.join(get_elemen_wajib(kategori))}</div>", unsafe_allow_html=True)
        
        foto_produk = st.file_uploader("Upload Foto Referensi", type=['png', 'jpg'], accept_multiple_files=True)
        foto_desc = []
        if foto_produk:
            st.markdown('<div class="photo-caption-box">🏷️ <b>Beri keterangan singkat tiap foto</b> (Mencegah halusinasi bentuk)</div>', unsafe_allow_html=True)
            for i, f in enumerate(foto_produk[:3]):
                c1, c2 = st.columns([1, 2.5])
                with c1: st.image(f, use_container_width=True)
                with c2: foto_desc.append(st.text_input(f"Desc Foto {i+1}", key=f"f_{i}", label_visibility="collapsed", placeholder="Contoh: Plastik hijau"))

    st.markdown('<div class="step-label">🎯 Langkah 3: Strategi Platform</div>', unsafe_allow_html=True)
    with st.container(border=True):
        platform = st.radio("Platform", ["Instagram", "WhatsApp", "TikTok"])
        cs1, cs2 = st.columns(2)
        with cs1: gaya = st.selectbox("Tone", ["Santai & Kekinian", "Profesional", "Hard-Selling"])
        with cs2: mood = st.selectbox("Mood", ["Cerah", "Gelap Elegan", "Hangat"])
        bg = st.selectbox("Background", list(BACKGROUND_OPTIONS.keys()))
        subjek = st.selectbox("Subjek", ["Produk saja", "1 Orang", "Keluarga"])

    if st.button("🚀 GENERATE IKLAN", type="primary", use_container_width=True):
        if not nama_produk: st.warning("Isi nama produk dulu!")
        else:
            st.session_state.img_mem = {"A": None, "B": None, "C": None}
            st.session_state.ai_review = None
            with st.spinner("AI sedang meracik copywriting..."):
                img_bytes = [f.getvalue() for f in foto_produk] if foto_produk else []
                res = generate_ad_text_master(kategori, nama_produk, keywords, gaya, platform, market, mood, bg, subjek, img_bytes, get_elemen_wajib(kategori), foto_desc)
                vis, txt = parse_output_for_image(res)
                st.session_state.main_txt, st.session_state.vis_prompt = txt, vis
                st.session_state.last_p = {"nama": nama_produk, "plat": platform}

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
            st.markdown('<div class="cost-badge">Estimasi Biaya API: ~$0.03 / Rp 480</div>', unsafe_allow_html=True)
            if st.button("Render Imagen 3.0", key="btn_a", use_container_width=True):
                with st.spinner("Merender Imagen via API murni..."):
                    raw = generate_imagen_image(vis_edit)
                    st.session_state.img_mem["A"] = apply_dynamic_branding(raw, logo_file, posisi_logo) if raw else None
            if st.session_state.img_mem["A"]:
                st.image(st.session_state.img_mem["A"], caption="Model A: Imagen 3.0")
                st.download_button("⬇️ Download Imagen", data=st.session_state.img_mem["A"], file_name="imagen_inamikro.png", mime="image/png", use_container_width=True)

        with t_dalle:
            st.markdown('<div class="cost-badge">Estimasi Biaya API: ~$0.05 / Rp 800</div>', unsafe_allow_html=True)
            if st.button("Render GPT/DALL-E", key="btn_b", use_container_width=True):
                with st.spinner("Merender via OpenAI (GPT-Image-2/DALL-E-2)..."):
                    raw = generate_dalle_image(vis_edit)
                    st.session_state.img_mem["B"] = apply_dynamic_branding(raw, logo_file, posisi_logo) if raw else None
            if st.session_state.img_mem["B"]:
                st.image(st.session_state.img_mem["B"], caption="Model B: GPT Image / DALL-E")
                st.download_button("⬇️ Download GPT", data=st.session_state.img_mem["B"], file_name="gpt_inamikro.png", mime="image/png", use_container_width=True)

        with t_gmn:
            st.markdown('<div class="cost-badge">Estimasi Biaya API: Termasuk Kuota Gemini / Gratis</div>', unsafe_allow_html=True)
            if st.button("Render Nano Banana 2", key="btn_c", use_container_width=True):
                with st.spinner("Merender Gambar..."):
                    raw = generate_gemini_flash_image(vis_edit)
                    st.session_state.img_mem["C"] = apply_dynamic_branding(raw, logo_file, posisi_logo) if raw else None
            if st.session_state.img_mem["C"]:
                st.image(st.session_state.img_mem["C"], caption="Model C: Gemini Nano Banana 2 / Fast Generate")
                st.download_button("⬇️ Download Gemini", data=st.session_state.img_mem["C"], file_name="gemini_inamikro.png", mime="image/png", use_container_width=True)
    else:
        st.info("👈 Silakan isi data di sebelah kiri lalu tekan Generate.")