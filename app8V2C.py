import os
import streamlit as st
import re
import io
import base64
from PIL import Image, ImageEnhance

# Import Vertex AI & LangChain
try:
    import vertexai
    from langchain_google_vertexai import ChatVertexAI
    from vertexai.vision_models import ImageGenerationModel
    from langchain_core.messages import HumanMessage
    IS_VERTEX_AVAILABLE = True
except ImportError:
    IS_VERTEX_AVAILABLE = False
    st.error("⚠️ Peringatan: Library Vertex AI / LangChain belum dipasang.")

# ==============================================================================
# BAGIAN 1: KONFIGURASI VERTEX AI (GCP)
# ==============================================================================
YOUR_PROJECT_ID = "careful-ensign-477104-p5"
YOUR_LOCATION = "us-central1"

VERTEX_CONNECTION_SUCCESS = False
try:
    if IS_VERTEX_AVAILABLE:
        vertexai.init(project=YOUR_PROJECT_ID, location=YOUR_LOCATION)
        VERTEX_CONNECTION_SUCCESS = True
except Exception as e:
    VERTEX_CONNECTION_SUCCESS = False
    print(f"Gagal init Vertex AI: {e}")

# ==============================================================================
# DATA KATEGORI KBLI INAMIKRO
# Tambahan Pak Greg: Deskripsi setiap sektor agar UMKM bisa memilih dengan tepat
# ==============================================================================
KBLI_DATA = {
    "56102 - Restoran dan Rumah Makan": {
        "desc": "Usaha yang menjual makanan siap saji di tempat makan, seperti warung, rumah makan, atau restoran.",
        "contoh": "Ayam geprek, warteg, nasi padang, bakso"
    },
    "56303 - Rumah Minum/Kafe": {
        "desc": "Usaha yang menjual minuman dan makanan ringan untuk dikonsumsi di tempat atau dibawa pulang.",
        "contoh": "Kopi susu, boba, kedai es, kafe"
    },
    "10794 - Industri Keripik & Makanan Ringan": {
        "desc": "Usaha produksi makanan ringan dalam kemasan untuk dijual.",
        "contoh": "Keripik singkong, basreng, makaroni pedas, snack"
    },
    "10750 - Industri Makanan Olahan (Frozen Food)": {
        "desc": "Usaha produksi makanan yang diproses dan dikemas, biasanya dibekukan.",
        "contoh": "Dimsum beku, nugget, bakso frozen, siomay kemasan"
    },
    "47841 - Perdagangan Eceran Makanan Keliling": {
        "desc": "Usaha berjualan makanan dan minuman secara keliling atau di pinggir jalan.",
        "contoh": "Martabak, roti bakar, es doger, gorengan gerobak"
    },
    "47711 - Perdagangan Eceran Pakaian (Fashion)": {
        "desc": "Usaha penjualan pakaian jadi secara eceran.",
        "contoh": "Gamis, kaos distro, kemeja, toko baju"
    },
    "47726 - Perdagangan Eceran Sepatu/Sandal": {
        "desc": "Usaha penjualan alas kaki secara eceran.",
        "contoh": "Sneakers, sandal kulit, sepatu boots, toko sepatu"
    },
    "96012 - Jasa Penatu/Laundry": {
        "desc": "Usaha jasa pencucian pakaian kiloan maupun satuan.",
        "contoh": "Laundry kiloan, cuci seprei, laundry express"
    },
    "96013 - Jasa Perawatan Sepatu/Tas": {
        "desc": "Usaha jasa membersihkan, memperbaiki, atau merawat sepatu dan tas.",
        "contoh": "Cuci sepatu, reparasi tas kulit, shoe care"
    },
    "85495 - Jasa Pendidikan/Bimbingan Belajar": {
        "desc": "Usaha jasa pendidikan nonformal seperti les privat atau bimbingan belajar.",
        "contoh": "Bimbel matematika, les bahasa Inggris, les musik"
    }
}
KBLI_CATEGORIES = list(KBLI_DATA.keys())

# Elemen wajib brosur per kategori (Tambahan Pak Greg: brosur UMKM harus ada elemen wajib)
BROSUR_ELEMEN_WAJIB = {
    "food": ["Nama Produk", "Harga", "Keunggulan/USP", "Promo/Diskon (jika ada)", "Cara Pemesanan / Call-to-Action", "Nomor Kontak / WhatsApp"],
    "fashion": ["Nama Brand", "Jenis Produk", "Ukuran Tersedia", "Harga", "Call-to-Action", "Nomor Kontak / WhatsApp"],
    "jasa": ["Nama Usaha", "Jenis Layanan", "Harga/Tarif", "Keunggulan", "Call-to-Action", "Nomor Kontak / WhatsApp"],
    "default": ["Nama Produk/Usaha", "Deskripsi Singkat", "Harga/Penawaran", "Call-to-Action", "Nomor Kontak"]
}

def get_elemen_wajib(kategori):
    if "Makanan" in kategori or "Restoran" in kategori or "Minum" in kategori or "Keripik" in kategori or "Eceran Makanan" in kategori:
        return BROSUR_ELEMEN_WAJIB["food"]
    elif "Pakaian" in kategori or "Sepatu" in kategori:
        return BROSUR_ELEMEN_WAJIB["fashion"]
    elif "Jasa" in kategori or "Penatu" in kategori or "Pendidikan" in kategori:
        return BROSUR_ELEMEN_WAJIB["jasa"]
    return BROSUR_ELEMEN_WAJIB["default"]

# ==============================================================================
# BAGIAN 2: ENGINE AI (AGENTIC PROMPTING & IMAGEN 3)
# ==============================================================================

def parse_output_for_image(markdown_text):
    """Memisahkan Ide Visual dari teks utama agar bisa diedit user (Revisi Pak Greg)."""
    try:
        match = re.search(r"\*\*Ide Visual:\*\*[\s]*(.*?)(?=\n\n|\Z)", markdown_text, re.IGNORECASE | re.DOTALL)
        if match:
            clean_idea = match.group(1).strip().replace('*', '').replace('\n', ' ')
            main_text = re.sub(r"\*\*Ide Visual:\*\*[\s]*(.*?)(?=\n\n|\Z)", "", markdown_text, flags=re.IGNORECASE | re.DOTALL)
            return clean_idea[:500], main_text.strip()
    except Exception:
        pass
    return "", markdown_text

@st.cache_data(show_spinner=False)
def generate_imagen_image(prompt_text):
    """Generate gambar menggunakan Imagen 3."""
    if not IS_VERTEX_AVAILABLE or not VERTEX_CONNECTION_SUCCESS or not prompt_text:
        return None
    full_prompt = (
        f"professional product photography, {prompt_text}, "
        "photorealistic, highly detailed, 8k resolution, "
        "commercial advertisement style, no text overlay, "
        "sharp focus, beautiful lighting."
    )
    try:
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        response = model.generate_images(prompt=full_prompt, number_of_images=1, aspect_ratio="1:1")
        return response.images[0]._image_bytes
    except Exception as e:
        st.error(f"Gagal generate gambar. Pesan dari Google: {e}")
        return None

try:
    llm_pro = ChatVertexAI(
        model_name="gemini-2.5-pro",
        temperature=0.3,
        max_output_tokens=8192
    )
except Exception:
    pass

@st.cache_data(show_spinner=False)
def generate_ad_text_agentic(kategori, user_input, gaya, platform, market, mood, images_bytes_list, elemen_wajib):
    """
    Agentic Prompting: AI berperan sebagai pakar sesuai kategori KBLI.
    Tambahan: Memastikan elemen wajib brosur ada di output (Revisi Pak Greg).
    Tambahan: Target market mempengaruhi gaya bahasa (Revisi Pak Felix).
    """
    market_str = ", ".join(market) if market else "Umum"
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])

    base_prompt = f"""ANDA ADALAH AGEN PAKAR MARKETING KHUSUS UNTUK KATEGORI UMKM: {kategori}.
TUGAS: Analisis input teks & gambar referensi. Buat copywriting iklan yang TEPAT SASARAN untuk target market yang ditentukan.

PROFIL KAMPANYE (WAJIB DIPATUHI 100%):
1. PRODUK & USP: {user_input}
2. TARGET MARKET: {market_str}
   → Sesuaikan gaya bahasa, pilihan kata, dan referensi budaya agar SANGAT RELEVAN dengan target ini.
3. GAYA BAHASA: {gaya}
4. MOOD VISUAL: {mood}
5. PLATFORM: {platform}

ELEMEN WAJIB BROSUR (Harus ada semua di dalam output):
{elemen_str}

ATURAN VISUAL (DUAL-FUSION):
- Analisis gambar referensi yang dilampirkan jika ada.
- Jika foto kolase, identifikasi produk utama berdasarkan deskripsi.
- Buat Ide Visual yang SANGAT DETAIL, mengacu pada produk asli tapi dalam suasana iklan profesional sesuai mood {mood}.
- DILARANG meniru teks/tulisan yang ada di foto referensi.

ATURAN STRICT: JANGAN basa-basi. LANGSUNG keluarkan output sesuai format.
"""

    if "Instagram" in platform:
        base_prompt += f"""
FORMAT WAJIB OUTPUT:
## 📸 Headline: [Headline catchy, maks 10 kata]

**Caption:**
[Caption menarik 2-3 paragraf, gunakan emoji relevan, sesuai tone {gaya} untuk target {market_str}]

**Hashtags:**
[6-10 hashtag relevan]

**Ide Visual:**
[SATU KALIMAT PANJANG BAHASA INGGRIS — deskripsi visual produk SANGAT DETAIL sesuai mood {mood}, no text in image, commercial photography style]
"""
    elif "WhatsApp" in platform:
        base_prompt += f"""
FORMAT WAJIB OUTPUT:
## 💬 Subject: [Judul pesan menarik]

**Isi Pesan:**
[Pesan broadcast persuasif, gunakan sapaan personal, cantumkan USP & promo, akhiri dengan CTA jelas + nomor kontak placeholder]

**Ide Visual:**
[SATU KALIMAT PANJANG BAHASA INGGRIS — deskripsi foto produk SANGAT DETAIL sesuai mood {mood}, no text in image]
"""
    elif "TikTok" in platform:
        base_prompt += f"""
FORMAT WAJIB OUTPUT:
## 🎬 Judul Video: [Hook judul yang viral]

**Scene 1 (Hook 0-3s):**
- **Visual Prompt (English):** [Deskripsi visual AI sangat detail]
- **Voiceover (Indonesian):** [Skrip audio hook]

**Scene 2 (Body 3-10s):**
- **Visual Prompt (English):** [Deskripsi visual AI sangat detail]
- **Voiceover (Indonesian):** [Skrip audio isi]

**Scene 3 (CTA 10-15s):**
- **Visual Prompt (English):** [Deskripsi visual AI sangat detail]
- **Voiceover (Indonesian):** [Skrip audio CTA]

**Ide Visual:**
[SATU KALIMAT PANJANG BAHASA INGGRIS — deskripsi thumbnail video sesuai mood {mood}, no text in image]
"""

    content_parts = [{"type": "text", "text": base_prompt}]
    for img_bytes in images_bytes_list:
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    return llm_pro.invoke([HumanMessage(content=content_parts)]).content


@st.cache_data(show_spinner=False)
def generate_ad_revision(kategori, user_input, gaya, platform, market, mood,
                          images_bytes_list, elemen_wajib, instruksi_revisi, teks_sebelumnya):
    """
    Chatbot Revisi: Merevisi hasil iklan berdasarkan instruksi user.
    Session state tetap, hanya bagian yang diminta yang diubah.
    """
    market_str = ", ".join(market) if market else "Umum"
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])

    revisi_prompt = f"""ANDA ADALAH AGEN PAKAR MARKETING KHUSUS UNTUK KATEGORI: {kategori}.

KONTEKS:
- Produk: {user_input}
- Target Market: {market_str}
- Gaya Bahasa: {gaya}
- Mood Visual: {mood}
- Platform: {platform}
- Elemen Wajib Brosur: {elemen_str}

HASIL IKLAN SEBELUMNYA:
{teks_sebelumnya}

🚨 INSTRUKSI REVISI DARI USER: {instruksi_revisi}

TUGAS: Revisi iklan di atas sesuai permintaan user. Pertahankan elemen yang tidak diminta untuk diubah.
Format output harus SAMA PERSIS dengan format sebelumnya (termasuk tag Ide Visual di paling bawah).
JANGAN basa-basi, langsung output hasil revisi.
"""

    content_parts = [{"type": "text", "text": revisi_prompt}]
    for img_bytes in images_bytes_list:
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    return llm_pro.invoke([HumanMessage(content=content_parts)]).content


@st.cache_data(show_spinner=False)
def evaluate_ad_quality(user_input, target_market, platform, elemen_wajib, generated_ad):
    """
    AI Expert Reviewer: Menilai kualitas iklan terhadap requirement.
    Revisi Pak Felix: Expert review / AI untuk cek hasil sesuai prompt/requirement berapa %.
    """
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])
    eval_prompt = f"""ANDA ADALAH JURI PAKAR DIGITAL MARKETING INDONESIA YANG NETRAL DAN OBJEKTIF.

SPESIFIKASI KAMPANYE (REQUIREMENT):
- Produk & USP: {user_input}
- Target Market: {target_market}
- Platform: {platform}
- Elemen Wajib yang Harus Ada:
{elemen_str}

HASIL IKLAN YANG DIEVALUASI:
{generated_ad}

TUGAS: Evaluasi hasil iklan ini secara objektif menggunakan 4 kriteria berikut:

1. RELEVANSI (0-25): Seberapa relevan iklan dengan produk & USP yang dideskripsikan?
2. KESESUAIAN TARGET (0-25): Seberapa tepat gaya bahasa & konten untuk target market?
3. KELENGKAPAN ELEMEN (0-25): Berapa banyak elemen wajib brosur yang terpenuhi?
4. KUALITAS COPYWRITING (0-25): Seberapa menarik dan persuasif teks iklannya?

FORMAT OUTPUT WAJIB:
**📊 Hasil Evaluasi AI Expert Reviewer:**

| Kriteria | Skor | Catatan |
|---|---|---|
| Relevansi Produk | X/25 | [catatan singkat] |
| Kesesuaian Target Market | X/25 | [catatan singkat] |
| Kelengkapan Elemen Wajib | X/25 | [catatan singkat] |
| Kualitas Copywriting | X/25 | [catatan singkat] |
| **TOTAL SKOR** | **XX/100** | |

**🏅 Kesimpulan:** [1-2 kalimat kesimpulan dan rekomendasi perbaikan utama]
"""
    return llm_pro.invoke(eval_prompt).content

# ==============================================================================
# BAGIAN 3: MANIPULASI LOGO DINAMIS (PILLOW)
# Revisi Pak Greg: Logo bisa pilih posisi, default kanan atas
# ==============================================================================

def apply_dynamic_branding(main_image_bytes, logo_file_uploaded, posisi):
    """Tempel logo di posisi yang dipilih user dengan opacity semi-transparan."""
    if not main_image_bytes or not logo_file_uploaded:
        return main_image_bytes
    try:
        main_img = Image.open(io.BytesIO(main_image_bytes))
        main_w, main_h = main_img.size

        logo_img = Image.open(logo_file_uploaded)
        if logo_img.mode != 'RGBA':
            logo_img = logo_img.convert('RGBA')

        new_logo_w = int(main_w * 0.18)
        new_logo_h = int(new_logo_w * (logo_img.height / logo_img.width))
        logo_img = logo_img.resize((new_logo_w, new_logo_h), Image.Resampling.LANCZOS)

        alpha = logo_img.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(0.88)
        logo_img.putalpha(alpha)

        padding = 28
        if posisi == "Kanan Atas":
            pos = (main_w - new_logo_w - padding, padding)
        elif posisi == "Kiri Atas":
            pos = (padding, padding)
        elif posisi == "Kanan Bawah":
            pos = (main_w - new_logo_w - padding, main_h - new_logo_h - padding)
        elif posisi == "Kiri Bawah":
            pos = (padding, main_h - new_logo_h - padding)
        else:
            pos = (main_w - new_logo_w - padding, padding)  # default kanan atas

        branded_img = main_img.copy()
        branded_img.paste(logo_img, pos, logo_img)

        img_byte_arr = io.BytesIO()
        branded_img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception as e:
        st.error(f"Gagal tempel logo: {e}")
        return main_image_bytes

# ==============================================================================
# BAGIAN 4: UI/UX STREAMLIT — VERSI V6 (FINAL)
# ==============================================================================

st.set_page_config(
    page_title="Inamikro Ad Generator V6",
    layout="wide",
    page_icon="📈"
)

# Custom CSS untuk tampilan lebih premium
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0 0.5rem 0;
    }
    .main-header h1 {
        color: #1E88E5;
        font-size: 2.2rem;
        margin-bottom: 0.2rem;
    }
    .main-header p {
        color: #666;
        font-size: 0.95rem;
    }
    .elemen-wajib-box {
        background: #f0f7ff;
        border-left: 4px solid #1E88E5;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin-top: 0.5rem;
        font-size: 0.85rem;
    }
    .kbli-desc {
        background: #f8f9fa;
        border-radius: 6px;
        padding: 0.5rem 0.8rem;
        font-size: 0.82rem;
        color: #555;
        margin-top: 0.3rem;
    }
    .step-label {
        font-weight: 700;
        font-size: 1.05rem;
        color: #1E88E5;
        margin-bottom: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>📈 Inamikro Ad Generator</h1>
    <p>Platform Pembuatan Konten Iklan UMKM Berbasis Agentic AI — Gemini 2.5 Pro & Imagen 3</p>
</div>
""", unsafe_allow_html=True)
st.divider()

if not VERTEX_CONNECTION_SUCCESS:
    st.error("⚠️ Sistem Offline: Gagal terhubung ke GCP Vertex AI. Jalankan: gcloud auth application-default login --project=careful-ensign-477104-p5")

# --- INISIALISASI SESSION STATE ---
if 'main_text_result' not in st.session_state:
    st.session_state.main_text_result = None
if 'visual_prompt_result' not in st.session_state:
    st.session_state.visual_prompt_result = None
if 'image_result_branded' not in st.session_state:
    st.session_state.image_result_branded = None
if 'ai_review_result' not in st.session_state:
    st.session_state.ai_review_result = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
# Simpan parameter terakhir untuk chatbot revisi
if 'last_params' not in st.session_state:
    st.session_state.last_params = {}

# --- LAYOUT UTAMA ---
col_form, col_result = st.columns([1, 1.45], gap="large")

# =========================================================
# KOLOM KIRI — FORM INPUT
# =========================================================
with col_form:

    # --- LANGKAH 1: BRANDING ---
    st.markdown('<div class="step-label">📋 Langkah 1: Branding UMKM</div>', unsafe_allow_html=True)
    with st.container(border=True):
        col_logo, col_pos = st.columns([1.2, 1])
        with col_logo:
            logo_umkm = st.file_uploader(
                "Upload Logo (PNG/JPG)",
                type=['png', 'jpg', 'jpeg'],
                help="Logo akan ditempelkan otomatis di gambar hasil AI"
            )
            if logo_umkm:
                st.image(logo_umkm, width=80, caption="Preview Logo")
        with col_pos:
            posisi_logo = st.selectbox(
                "Posisi Logo",
                ["Kanan Atas", "Kiri Atas", "Kanan Bawah", "Kiri Bawah"],
                index=0,
                help="Default: Kanan Atas"
            )

        target_market = st.multiselect(
            "Target Market",
            ["Mahasiswa", "Pekerja Kantoran", "Ibu Rumah Tangga",
             "Anak Sekolah / Remaja", "Pelaku Bisnis", "Umum"],
            default=["Umum"],
            help="Pilih siapa target pembeli produk ini. Mempengaruhi gaya bahasa AI."
        )

    # --- LANGKAH 2: DATA PRODUK ---
    st.markdown('<div class="step-label">📝 Langkah 2: Data Produk & Referensi Visual</div>', unsafe_allow_html=True)
    with st.container(border=True):
        nama_produk = st.text_input("Nama Produk / Brand", placeholder="Contoh: Bakwan Sowan")
        deskripsi = st.text_area(
            "Deskripsi Produk (USP)",
            placeholder="Contoh: Bakwan isi keju creamy lumer, varian siomay nori, harga 5rb-an.",
            height=85
        )

        # Pemilihan kategori dengan deskripsi (Revisi Pak Greg)
        kategori = st.selectbox("Kategori Usaha (KBLI Inamikro)", KBLI_CATEGORIES)
        kbli_info = KBLI_DATA[kategori]
        st.markdown(f"""
        <div class="kbli-desc">
            📌 <b>Deskripsi sektor:</b> {kbli_info['desc']}<br>
            💡 <b>Contoh usaha:</b> {kbli_info['contoh']}
        </div>
        """, unsafe_allow_html=True)

        # Tampilkan elemen wajib brosur (Revisi Pak Greg)
        elemen_wajib = get_elemen_wajib(kategori)
        elemen_html = "".join([f"<li>{e}</li>" for e in elemen_wajib])
        st.markdown(f"""
        <div class="elemen-wajib-box">
            <b>📋 Elemen Wajib Brosur untuk kategori ini:</b>
            <ul style="margin:0.3rem 0 0 0; padding-left:1.2rem;">{elemen_html}</ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Upload gambar produk — bisa lebih dari 1 (Revisi Pak Greg Bimbingan 4)
        product_images = st.file_uploader(
            "Upload Foto Referensi Produk (bisa lebih dari 1)",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            help="AI (Gemini Pro) akan menganalisis visual asli produk sebagai referensi"
        )

        # Preview gambar yang diupload
        if product_images:
            st.markdown("*Preview Foto Referensi:*")
            preview_cols = st.columns(min(len(product_images), 4))
            for idx, img_file in enumerate(product_images[:4]):
                with preview_cols[idx]:
                    st.image(img_file, use_container_width=True, caption=f"Foto {idx+1}")

    # --- LANGKAH 3: STRATEGI PLATFORM ---
    st.markdown('<div class="step-label">🎯 Langkah 3: Strategi Platform & Tone</div>', unsafe_allow_html=True)
    with st.container(border=True):
        platform = st.radio(
            "Platform Distribusi",
            ["Instagram (Visual & Feed)", "WhatsApp (Broadcast)", "TikTok (Video AI Script)"],
            horizontal=False
        )
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            gaya = st.selectbox(
                "Tone of Voice",
                ["Santai & Kekinian", "Profesional & Elegan", "Promo Hard-Selling"]
            )
        with col_s2:
            mood_visual = st.selectbox(
                "Mood Visual",
                ["Cerah & Ceria", "Gelap & Elegan", "Minimalis & Clean", "Hangat & Estetik"]
            )

    st.markdown("<br>", unsafe_allow_html=True)
    btn_generate = st.button(
        "🚀 GENERATE IKLAN SEKARANG",
        type="primary",
        use_container_width=True,
        disabled=not VERTEX_CONNECTION_SUCCESS
    )

# =========================================================
# KOLOM KANAN — OUTPUT
# =========================================================
with col_result:
    st.markdown('<div class="step-label">📱 Langkah 4: Hasil Produksi AI</div>', unsafe_allow_html=True)

    # --- GENERATE IKLAN ---
    if btn_generate:
        if not nama_produk or not deskripsi:
            st.warning("⚠️ Lengkapi Nama Produk dan Deskripsi terlebih dahulu.")
        else:
            st.session_state.image_result_branded = None
            st.session_state.ai_review_result = None
            st.session_state.chat_history = []

            with st.spinner("🧠 Agen AI sedang menganalisis target market & referensi visual..."):
                images_data = [img.getvalue() for img in product_images] if product_images else []
                raw_res = generate_ad_text_agentic(
                    kategori,
                    f"{nama_produk}: {deskripsi}",
                    gaya, platform, target_market,
                    mood_visual, images_data, elemen_wajib
                )
                vis_prompt, main_txt = parse_output_for_image(raw_res)
                st.session_state.main_text_result = main_txt
                st.session_state.visual_prompt_result = vis_prompt

            # Simpan parameter untuk chatbot revisi
            st.session_state.last_params = {
                "kategori": kategori,
                "user_input": f"{nama_produk}: {deskripsi}",
                "gaya": gaya,
                "platform": platform,
                "market": target_market,
                "mood": mood_visual,
                "images_data": [img.getvalue() for img in product_images] if product_images else [],
                "elemen_wajib": elemen_wajib
            }

    # --- TAMPILKAN HASIL TEKS ---
    if st.session_state.main_text_result:
        with st.container(border=True):
            st.markdown(st.session_state.main_text_result)

            # AI Expert Reviewer (Revisi Pak Felix)
            st.divider()
            col_ev1, col_ev2 = st.columns([1, 1])
            with col_ev1:
                if st.button("🤖 Minta Penilaian AI Expert Reviewer", use_container_width=True):
                    with st.spinner("Juri AI sedang mengevaluasi kualitas iklan..."):
                        market_str = ", ".join(target_market) if target_market else "Umum"
                        st.session_state.ai_review_result = evaluate_ad_quality(
                            f"{nama_produk}: {deskripsi}",
                            market_str, platform,
                            elemen_wajib,
                            st.session_state.main_text_result
                        )

        if st.session_state.ai_review_result:
            with st.container(border=True):
                st.markdown(st.session_state.ai_review_result)

        # --- TAHAP PRA-RENDER: EDIT IDE VISUAL (Revisi Pak Greg) ---
        st.divider()
        st.markdown("#### 🎨 Langkah 5: Pra-Render — Edit Prompt Visual")
        st.caption(
            "AI merumuskan prompt gambar di bawah ini berdasarkan deskripsi produk & foto referensi. "
            "Anda dapat mengedit atau menambahkan detail sebelum gambar dirender oleh Imagen 3."
        )

        edited_visual_prompt = st.text_area(
            "Instruksi ke Imagen 3 (Editable — Bahasa Inggris):",
            value=st.session_state.visual_prompt_result,
            height=90,
            key="visual_prompt_editor"
        )

        if edited_visual_prompt:
            if st.button("✨ RENDER GAMBAR (Imagen 3) + TEMPEL LOGO", type="primary", use_container_width=True):
                with st.spinner("Memproses gambar resolusi tinggi dengan Imagen 3..."):
                    img_raw_bytes = generate_imagen_image(edited_visual_prompt)

                    if img_raw_bytes:
                        if logo_umkm:
                            with st.spinner(f"Menempelkan logo di posisi {posisi_logo}..."):
                                st.session_state.image_result_branded = apply_dynamic_branding(
                                    img_raw_bytes, logo_umkm, posisi_logo
                                )
                        else:
                            st.session_state.image_result_branded = img_raw_bytes
                        st.balloons()
                    else:
                        st.error("Gagal menghasilkan gambar. Coba ulangi atau periksa koneksi Vertex AI.")

    # --- TAMPILKAN HASIL GAMBAR ---
    if st.session_state.image_result_branded:
        with st.container(border=True):
            st.markdown("#### 🖼️ Hasil Visual Final (Imagen 3 + Logo)")
            col_pad1, col_img, col_pad2 = st.columns([0.5, 3, 0.5])
            with col_img:
                st.image(
                    st.session_state.image_result_branded,
                    use_container_width=True,
                    caption=f"Visual iklan profesional untuk {nama_produk}"
                )
                st.download_button(
                    label="⬇️ Download Visual Final (PNG)",
                    data=st.session_state.image_result_branded,
                    file_name=f"iklan_{nama_produk.replace(' ', '_').lower()}.png",
                    mime="image/png",
                    use_container_width=True
                )

    # --- PLACEHOLDER SAAT KOSONG ---
    if not st.session_state.main_text_result:
        with st.container(border=True):
            st.info("👈 Isi form di panel kiri, lalu klik 'GENERATE IKLAN SEKARANG' untuk memulai.")

    # =========================================================
    # LANGKAH 6: CHATBOT REVISI (dari V4, dikembalikan + disempurnakan)
    # Revisi: Session state dijaga, history percakapan ditampilkan
    # =========================================================
    if st.session_state.main_text_result:
        st.divider()
        st.markdown("#### 🤖 Langkah 6: Asisten Revisi Cepat")
        st.caption(
            "Kurang puas? Ketik instruksi revisi di bawah. "
            "AI akan merevisi teks iklan sesuai permintaan tanpa mengulang dari awal. "
            "Contoh: *'Buat caption lebih pendek'*, *'Ganti mood visual jadi lebih gelap'*, "
            "*'Tambahkan promo diskon 20%'*"
        )

        # Tampilkan history chat
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        revisi_input = st.chat_input("Ketik instruksi revisi di sini...")

        if revisi_input and st.session_state.last_params:
            # Tambah pesan user ke history
            st.session_state.chat_history.append({"role": "user", "content": revisi_input})

            with st.chat_message("user"):
                st.markdown(revisi_input)

            with st.chat_message("assistant"):
                with st.spinner("🧠 Gemini Pro sedang merevisi..."):
                    p = st.session_state.last_params
                    new_raw = generate_ad_revision(
                        p["kategori"], p["user_input"], p["gaya"],
                        p["platform"], p["market"], p["mood"],
                        p["images_data"], p["elemen_wajib"],
                        instruksi_revisi=revisi_input,
                        teks_sebelumnya=st.session_state.main_text_result
                    )

                    new_vis_prompt, new_main_txt = parse_output_for_image(new_raw)

                    # Update session state
                    st.session_state.main_text_result = new_main_txt
                    st.session_state.visual_prompt_result = new_vis_prompt
                    st.session_state.image_result_branded = None
                    st.session_state.ai_review_result = None

                    confirmation_msg = "✅ Iklan sudah direvisi! Scroll ke atas untuk melihat hasil terbaru, lalu klik **Render Gambar** jika ingin memperbarui visual."
                    st.markdown(confirmation_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": confirmation_msg
                    })

            st.rerun()