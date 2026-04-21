import os
import streamlit as st
import re
import io
import base64
from PIL import Image, ImageEnhance, ImageDraw, ImageFont

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
# Revisi Pak Greg: Deskripsi setiap sektor agar UMKM bisa memilih dengan tepat
# ==============================================================================
KBLI_DATA = {
    "56102 - Restoran dan Rumah Makan": {
        "desc": "Usaha yang menjual makanan siap saji di tempat makan.",
        "contoh": "Ayam geprek, warteg, nasi padang, bakso",
        "tipe": "food"
    },
    "56303 - Rumah Minum/Kafe": {
        "desc": "Usaha yang menjual minuman dan makanan ringan di tempat atau dibawa pulang.",
        "contoh": "Kopi susu, boba, kedai es, kafe",
        "tipe": "food"
    },
    "10794 - Industri Keripik & Makanan Ringan": {
        "desc": "Usaha produksi makanan ringan dalam kemasan untuk dijual.",
        "contoh": "Keripik singkong, basreng, makaroni pedas, snack",
        "tipe": "food"
    },
    "10750 - Industri Makanan Olahan (Frozen Food)": {
        "desc": "Usaha produksi makanan yang diproses dan dikemas, biasanya dibekukan.",
        "contoh": "Dimsum beku, nugget, bakso frozen, siomay kemasan",
        "tipe": "food"
    },
    "47841 - Perdagangan Eceran Makanan Keliling": {
        "desc": "Usaha berjualan makanan dan minuman secara keliling atau di pinggir jalan.",
        "contoh": "Martabak, roti bakar, es doger, gorengan gerobak",
        "tipe": "food"
    },
    "47711 - Perdagangan Eceran Pakaian (Fashion)": {
        "desc": "Usaha penjualan pakaian jadi secara eceran.",
        "contoh": "Gamis, kaos distro, kemeja, toko baju",
        "tipe": "fashion"
    },
    "47726 - Perdagangan Eceran Sepatu/Sandal": {
        "desc": "Usaha penjualan alas kaki secara eceran.",
        "contoh": "Sneakers, sandal kulit, sepatu boots, toko sepatu",
        "tipe": "fashion"
    },
    "96012 - Jasa Penatu/Laundry": {
        "desc": "Usaha jasa pencucian pakaian kiloan maupun satuan.",
        "contoh": "Laundry kiloan, cuci seprei, laundry express",
        "tipe": "jasa"
    },
    "96013 - Jasa Perawatan Sepatu/Tas": {
        "desc": "Usaha jasa membersihkan, memperbaiki, atau merawat sepatu dan tas.",
        "contoh": "Cuci sepatu, reparasi tas kulit, shoe care",
        "tipe": "jasa"
    },
    "85495 - Jasa Pendidikan/Bimbingan Belajar": {
        "desc": "Usaha jasa pendidikan nonformal seperti les privat atau bimbingan belajar.",
        "contoh": "Bimbel matematika, les bahasa Inggris, les musik",
        "tipe": "jasa"
    }
}
KBLI_CATEGORIES = list(KBLI_DATA.keys())

# Elemen wajib brosur per tipe (Revisi Pak Greg)
BROSUR_ELEMEN = {
    "food": ["Nama Produk", "Harga", "Keunggulan/USP", "Promo/Diskon (jika ada)", "Call-to-Action", "Kontak/WhatsApp"],
    "fashion": ["Nama Brand", "Jenis Produk", "Ukuran Tersedia", "Harga", "Call-to-Action", "Kontak/WhatsApp"],
    "jasa": ["Nama Usaha", "Jenis Layanan", "Harga/Tarif", "Keunggulan", "Call-to-Action", "Kontak/WhatsApp"],
}

def get_elemen_wajib(kategori):
    tipe = KBLI_DATA.get(kategori, {}).get("tipe", "food")
    return BROSUR_ELEMEN.get(tipe, BROSUR_ELEMEN["food"])

# Pilihan background/environment — dropdown, tidak perlu ngetik (Pak Felix)
BACKGROUND_OPTIONS = {
    "🍽️ Meja Kayu Estetik": "rustic wooden table with warm bokeh background",
    "⬛ Studio Gelap Elegan": "dark matte studio background with dramatic side lighting",
    "🌿 Alam Hijau Segar": "fresh green leaves natural outdoor background",
    "⬜ Studio Putih Bersih": "clean white studio background with soft shadows",
    "🧱 Bata Industrial": "industrial brick wall background with warm lighting",
    "🌸 Pastel Aesthetic": "soft pastel pink and cream aesthetic background",
    "🎋 Bambu / Tradisional": "bamboo mat traditional Indonesian background",
    "✨ Gradient Premium": "smooth dark gradient luxury background with golden accent",
}

# Pilihan subjek — dropdown, tidak ngetik (Pak Felix)
SUBJEK_OPTIONS = [
    "Produk saja (tanpa orang)",
    "1 orang — pria muda",
    "1 orang — wanita muda",
    "1 orang — ibu rumah tangga",
    "2 orang — teman / pasangan",
    "Keluarga kecil (3-4 orang)",
    "Suasana ramai (banyak orang di latar)",
]

MOOD_OPTIONS = ["Cerah & Ceria", "Gelap & Elegan", "Minimalis & Clean", "Hangat & Estetik", "Playful & Colorful"]

# ==============================================================================
# BAGIAN 2: ENGINE AI
# ==============================================================================

def parse_output_for_image(markdown_text):
    """Pisahkan Ide Visual dari teks utama."""
    try:
        match = re.search(
            r"\*\*Ide Visual:\*\*[\s]*(.*?)(?=\n\n|\Z)",
            markdown_text, re.IGNORECASE | re.DOTALL
        )
        if match:
            clean_idea = match.group(1).strip().replace('*', '').replace('\n', ' ')
            main_text = re.sub(
                r"\*\*Ide Visual:\*\*[\s]*(.*?)(?=\n\n|\Z)", "",
                markdown_text, flags=re.IGNORECASE | re.DOTALL
            )
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
        "sharp focus, beautiful cinematic lighting."
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
def generate_ad_text_agentic(
    kategori, nama_produk, keywords_list, gaya, platform,
    market, mood, background, subjek, images_bytes_list, elemen_wajib
):
    """
    Agentic Prompting.
    - Input keyword (bukan free text) → kurangi halusinasi (Pak Felix)
    - Background & subjek sudah dipilih → AI lebih terarah
    - Elemen wajib brosur selalu ada (Pak Greg)
    """
    market_str = ", ".join(market) if market else "Umum"
    keywords_str = ", ".join(keywords_list) if keywords_list else nama_produk
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])
    bg_desc = BACKGROUND_OPTIONS.get(background, background)

    base_prompt = f"""ANDA ADALAH AGEN PAKAR MARKETING KHUSUS UNTUK KATEGORI UMKM: {kategori}.
TUGAS: Buat copywriting iklan profesional berdasarkan input terstruktur.

=== INPUT TERSTRUKTUR ===
NAMA PRODUK: {nama_produk}
KEYWORD USP: {keywords_str}
TARGET MARKET: {market_str}
GAYA BAHASA: {gaya}
MOOD VISUAL: {mood}
BACKGROUND/ENVIRONMENT: {bg_desc}
SUBJEK DALAM GAMBAR: {subjek}
PLATFORM: {platform}

=== ELEMEN WAJIB BROSUR (Harus semua ada di output) ===
{elemen_str}

=== ATURAN VISUAL (DUAL-FUSION) ===
- Jika ada foto referensi: analisis produk utama, replika komposisi, buat versi iklan profesional.
- Ide Visual HARUS mencantumkan: environment ({bg_desc}), subjek ({subjek}), mood ({mood}).
- DILARANG meniru teks/tulisan dari foto referensi.
- DILARANG basa-basi. Langsung output sesuai format di bawah.

=== ATURAN ANTI-HALUSINASI ===
- Gunakan HANYA informasi dari keyword yang diberikan.
- Jangan mengarang detail produk yang tidak disebutkan dalam keyword.
"""

    if "Instagram" in platform:
        base_prompt += f"""
FORMAT WAJIB OUTPUT:
## 📸 Headline: [Headline catchy, maks 10 kata]

**Caption:**
[Caption 2-3 paragraf, emoji relevan, tone {gaya} untuk target {market_str}]

**Hashtags:**
[6-10 hashtag relevan]

**Ide Visual:**
[SATU KALIMAT PANJANG BAHASA INGGRIS — deskripsi SANGAT DETAIL: environment ({bg_desc}), subjek ({subjek}), mood ({mood}), no text in image, commercial photography style]
"""
    elif "WhatsApp" in platform:
        base_prompt += f"""
FORMAT WAJIB OUTPUT:
## 💬 Subject: [Judul pesan menarik]

**Isi Pesan:**
[Broadcast persuasif, sapaan personal, USP dari keyword, promo, CTA + kontak placeholder]

**Ide Visual:**
[SATU KALIMAT PANJANG BAHASA INGGRIS — foto produk SANGAT DETAIL: environment ({bg_desc}), mood ({mood}), no text in image]
"""
    elif "TikTok" in platform:
        base_prompt += f"""
FORMAT WAJIB OUTPUT:
## 🎬 Judul Video: [Hook judul viral]

**Scene 1 (Hook 0-3s):**
- **Visual Prompt (English):** [Detail visual AI — environment {bg_desc}, subjek {subjek}]
- **Voiceover (Indonesian):** [Skrip audio hook]

**Scene 2 (Body 3-10s):**
- **Visual Prompt (English):** [Detail visual AI — close up produk, mood {mood}]
- **Voiceover (Indonesian):** [Skrip audio isi]

**Scene 3 (CTA 10-15s):**
- **Visual Prompt (English):** [Detail visual AI — CTA visual]
- **Voiceover (Indonesian):** [Skrip audio CTA]

**Ide Visual:**
[SATU KALIMAT PANJANG BAHASA INGGRIS — thumbnail: environment ({bg_desc}), mood ({mood}), no text in image]
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
def generate_ad_revision(
    kategori, nama_produk, keywords_list, gaya, platform,
    market, mood, background, subjek, images_bytes_list,
    elemen_wajib, instruksi_revisi, teks_sebelumnya
):
    """Revisi iklan. Format tetap, isi diperbarui sesuai instruksi."""
    market_str = ", ".join(market) if market else "Umum"
    keywords_str = ", ".join(keywords_list) if keywords_list else nama_produk
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])
    bg_desc = BACKGROUND_OPTIONS.get(background, background)

    revisi_prompt = f"""ANDA ADALAH AGEN PAKAR MARKETING KHUSUS KATEGORI: {kategori}.

KONTEKS KAMPANYE:
- Produk: {nama_produk} | Keywords: {keywords_str}
- Target: {market_str} | Tone: {gaya} | Platform: {platform}
- Mood: {mood} | Background: {bg_desc} | Subjek: {subjek}
- Elemen Wajib: {elemen_str}

HASIL IKLAN SEBELUMNYA:
{teks_sebelumnya}

INSTRUKSI REVISI DARI USER: {instruksi_revisi}

TUGAS: Revisi iklan sesuai permintaan. Pertahankan format yang sama persis.
PENTING: Bagian **Ide Visual:** di paling bawah HARUS SELALU ADA dan diperbarui jika revisi menyangkut visual.
JANGAN basa-basi. Langsung output hasil revisi lengkap.
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
def evaluate_ad_quality(nama_produk, keywords_list, target_market, platform, elemen_wajib, generated_ad):
    """
    AI Expert Reviewer — nilai iklan vs requirement dalam persen.
    Revisi Pak Felix: harus ada skor % sesuai prompt/requirement.
    """
    keywords_str = ", ".join(keywords_list) if keywords_list else nama_produk
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])
    market_str = ", ".join(target_market) if target_market else "Umum"

    eval_prompt = f"""ANDA ADALAH JURI PAKAR DIGITAL MARKETING INDONESIA YANG NETRAL DAN OBJEKTIF.
Evaluasi iklan berikut terhadap requirement/spesifikasi UMKM.

=== REQUIREMENT (Prompt Input) ===
- Nama Produk: {nama_produk}
- Keyword USP: {keywords_str}
- Target Market: {market_str}
- Platform: {platform}
- Elemen Wajib Brosur:
{elemen_str}

=== HASIL IKLAN (Output yang Dievaluasi) ===
{generated_ad}

=== KRITERIA EVALUASI (masing-masing 0-25 poin) ===
1. RELEVANSI PRODUK: Sesuai dengan nama produk & keyword USP?
2. KESESUAIAN TARGET MARKET: Gaya bahasa & konten cocok untuk target {market_str}?
3. KELENGKAPAN ELEMEN WAJIB: Berapa elemen dari {len(elemen_wajib)} yang terpenuhi?
4. KUALITAS COPYWRITING: Seberapa menarik, persuasif, dan profesional?

FORMAT OUTPUT WAJIB:
**📊 Hasil Evaluasi AI Expert Reviewer:**

| Kriteria | Skor | Catatan |
|---|---|---|
| Relevansi Produk | X/25 | [catatan singkat] |
| Kesesuaian Target Market | X/25 | [catatan singkat] |
| Kelengkapan Elemen Wajib | X/25 | [catatan singkat] |
| Kualitas Copywriting | X/25 | [catatan singkat] |
| **TOTAL SKOR** | **XX/100** | **XX%** |

**✅ Kekuatan Utama:** [1 kalimat]
**⚠️ Rekomendasi Perbaikan:** [1-2 kalimat]
"""
    return llm_pro.invoke(eval_prompt).content


# ==============================================================================
# BAGIAN 3: MANIPULASI GAMBAR — LOGO + TEXT OVERLAY
# ==============================================================================

def apply_dynamic_branding(main_image_bytes, logo_file_uploaded, posisi):
    """Tempel logo di posisi yang dipilih dengan opacity semi-transparan."""
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
        else:
            pos = (padding, main_h - new_logo_h - padding)

        branded_img = main_img.copy()
        branded_img.paste(logo_img, pos, logo_img)

        img_byte_arr = io.BytesIO()
        branded_img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception as e:
        st.error(f"Gagal tempel logo: {e}")
        return main_image_bytes


def add_text_overlay(main_image_bytes, teks_overlay, posisi_teks, ukuran_font, warna_teks):
    """
    Tambahkan teks/tulisan ke gambar hasil AI.
    Tambahan Pak Felix: image bisa ditambah text-based (keyword/tagline pendek).
    """
    if not main_image_bytes or not teks_overlay.strip():
        return main_image_bytes
    try:
        main_img = Image.open(io.BytesIO(main_image_bytes)).convert("RGBA")
        main_w, main_h = main_img.size

        txt_layer = Image.new("RGBA", main_img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        try:
            font = ImageFont.truetype("arial.ttf", ukuran_font)
        except Exception:
            font = ImageFont.load_default()

        try:
            bbox = draw.textbbox((0, 0), teks_overlay, font=font)
            teks_w = bbox[2] - bbox[0]
            teks_h = bbox[3] - bbox[1]
        except Exception:
            teks_w = len(teks_overlay) * ukuran_font // 2
            teks_h = ukuran_font + 10

        padding = 30
        if posisi_teks == "Tengah Atas":
            pos = ((main_w - teks_w) // 2, padding)
        elif posisi_teks == "Tengah Bawah":
            pos = ((main_w - teks_w) // 2, main_h - teks_h - padding)
        elif posisi_teks == "Kiri Atas":
            pos = (padding, padding)
        elif posisi_teks == "Kanan Bawah":
            pos = (main_w - teks_w - padding, main_h - teks_h - padding)
        else:
            pos = ((main_w - teks_w) // 2, (main_h - teks_h) // 2)

        shadow_offset = max(2, ukuran_font // 20)
        draw.text(
            (pos[0] + shadow_offset, pos[1] + shadow_offset),
            teks_overlay, font=font, fill=(0, 0, 0, 180)
        )

        color_map = {
            "⬜ Putih": (255, 255, 255, 240),
            "🟡 Kuning": (255, 220, 0, 240),
            "🟠 Oranye": (255, 120, 0, 240),
            "⬛ Hitam": (20, 20, 20, 240),
            "🔴 Merah": (220, 30, 30, 240),
        }
        fill_color = color_map.get(warna_teks, (255, 255, 255, 240))
        draw.text(pos, teks_overlay, font=font, fill=fill_color)

        result = Image.alpha_composite(main_img, txt_layer).convert("RGB")
        img_byte_arr = io.BytesIO()
        result.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception as e:
        st.error(f"Gagal tambah teks: {e}")
        return main_image_bytes


# ==============================================================================
# BAGIAN 4: UI/UX STREAMLIT — V6 FINAL
# ==============================================================================

st.set_page_config(
    page_title="Inamikro Ad Generator V6",
    layout="wide",
    page_icon="📈"
)

st.markdown("""
<style>
    .main-header { text-align: center; padding: 0.8rem 0 0.3rem 0; }
    .main-header h1 { color: #1565C0; font-size: 2rem; margin-bottom: 0.1rem; }
    .main-header p { color: #666; font-size: 0.9rem; }
    .step-label {
        font-weight: 700; font-size: 1rem; color: #1565C0;
        margin: 0.8rem 0 0.3rem 0; padding-left: 2px;
    }
    .kbli-desc {
        background: #f0f4ff; border-left: 3px solid #1565C0;
        border-radius: 4px; padding: 0.4rem 0.7rem;
        font-size: 0.81rem; color: #444; margin-top: 0.3rem;
    }
    .elemen-box {
        background: #f7fff7; border-left: 3px solid #2e7d32;
        border-radius: 4px; padding: 0.4rem 0.7rem;
        font-size: 0.81rem; margin-top: 0.3rem;
    }
    .kw-tag {
        background:#e3f2fd; border-radius:12px; padding:2px 10px;
        font-size:0.8rem; color:#1565C0; margin:2px; display:inline-block;
    }
    .info-note {
        background:#fff8e1; border-left:3px solid #f9a825;
        border-radius:4px; padding:0.3rem 0.6rem;
        font-size:0.8rem; color:#555; margin-bottom:0.3rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>📈 Inamikro Ad Generator</h1>
    <p>Platform Konten Iklan UMKM Berbasis Agentic AI — Gemini 2.5 Pro & Imagen 3 &nbsp;|&nbsp; Versi 6</p>
</div>
""", unsafe_allow_html=True)
st.divider()

if not VERTEX_CONNECTION_SUCCESS:
    st.error(
        "⚠️ Sistem Offline. Jalankan di terminal: "
        "`gcloud auth application-default login --project=careful-ensign-477104-p5`"
    )

# --- SESSION STATE ---
defaults = {
    'main_text_result': None,
    'visual_prompt_result': None,
    'image_result_final': None,
    'ai_review_result': None,
    'chat_history': [],
    'last_params': {},
    'visual_prompt_version': 0,   # increment ini untuk force-refresh editor Langkah 5
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================================================
# LAYOUT
# =========================================================
col_form, col_result = st.columns([1, 1.45], gap="large")

# =========================================================
# KOLOM KIRI — FORM INPUT
# =========================================================
with col_form:

    # LANGKAH 1: BRANDING
    st.markdown('<div class="step-label">📋 Langkah 1: Identitas & Branding UMKM</div>', unsafe_allow_html=True)
    with st.container(border=True):
        col_logo, col_pos = st.columns([1.3, 1])
        with col_logo:
            logo_umkm = st.file_uploader(
                "Upload Logo UMKM (PNG/JPG)",
                type=['png', 'jpg', 'jpeg'],
                help="Logo ditempel otomatis di gambar hasil AI"
            )
            if logo_umkm:
                st.image(logo_umkm, width=70, caption="Preview Logo")
        with col_pos:
            posisi_logo = st.selectbox(
                "Posisi Logo",
                ["Kanan Atas", "Kiri Atas", "Kanan Bawah", "Kiri Bawah"],
                index=0
            )
        target_market = st.multiselect(
            "🎯 Target Market",
            ["Mahasiswa", "Pekerja Kantoran", "Ibu Rumah Tangga",
             "Anak Sekolah / Remaja", "Pelaku Bisnis", "Umum"],
            default=["Umum"],
            help="Mempengaruhi gaya bahasa dan isi iklan"
        )

    # LANGKAH 2: DATA PRODUK
    st.markdown('<div class="step-label">📝 Langkah 2: Data Produk & Referensi Visual</div>', unsafe_allow_html=True)
    with st.container(border=True):
        nama_produk = st.text_input("Nama Produk / Brand", placeholder="Contoh: Bakwan Sowan")

        # KEYWORD — bukan free text panjang (Pak Felix: kurangi halusinasi, batasi input)
        st.markdown(
            '<div class="info-note">💡 Isi kata kunci keunggulan produk, pisahkan dengan koma. '
            'Maks 10 kata per keyword. Jangan kalimat panjang.</div>',
            unsafe_allow_html=True
        )
        keywords_raw = st.text_input(
            "Keyword USP Produk",
            placeholder="Contoh: keju creamy, siomay nori, halal, harga terjangkau",
            help="Keyword singkat membantu AI tidak berhalusinasi"
        )
        keywords_list = [k.strip() for k in keywords_raw.split(",") if k.strip()]

        if keywords_list:
            tags_html = " ".join([f'<span class="kw-tag">{k}</span>' for k in keywords_list])
            st.markdown(tags_html, unsafe_allow_html=True)

        kategori = st.selectbox("Kategori Usaha (KBLI Inamikro)", KBLI_CATEGORIES)
        kbli_info = KBLI_DATA[kategori]
        st.markdown(f"""
        <div class="kbli-desc">
            📌 <b>Sektor:</b> {kbli_info['desc']}<br>
            💡 <b>Contoh usaha:</b> {kbli_info['contoh']}
        </div>
        """, unsafe_allow_html=True)

        elemen_wajib = get_elemen_wajib(kategori)
        elemen_html = "".join([f"<li>{e}</li>" for e in elemen_wajib])
        st.markdown(f"""
        <div class="elemen-box">
            <b>✅ Elemen wajib brosur kategori ini:</b>
            <ul style="margin:0.2rem 0 0 0;padding-left:1.1rem;">{elemen_html}</ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Upload foto referensi — bisa lebih dari 1 (Bimbingan 4, Pak Greg)
        product_images = st.file_uploader(
            "📷 Upload Foto Referensi Produk (bisa lebih dari 1)",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            help="AI menganalisis visual asli sebagai referensi iklan"
        )
        if product_images:
            st.markdown("*Preview foto referensi:*")
            prev_cols = st.columns(min(len(product_images), 4))
            for idx, img_file in enumerate(product_images[:4]):
                with prev_cols[idx]:
                    st.image(img_file, use_container_width=True, caption=f"Foto {idx+1}")

    # LANGKAH 3: STRATEGI PLATFORM & VISUAL
    st.markdown('<div class="step-label">🎯 Langkah 3: Strategi Platform & Visual</div>', unsafe_allow_html=True)
    with st.container(border=True):
        platform = st.radio(
            "Platform Distribusi",
            ["Instagram (Visual & Feed)", "WhatsApp (Broadcast)", "TikTok (Video AI Script)"]
        )
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            gaya = st.selectbox(
                "Tone of Voice",
                ["Santai & Kekinian", "Profesional & Elegan", "Promo Hard-Selling"]
            )
        with col_s2:
            mood_visual = st.selectbox("Mood Visual", MOOD_OPTIONS)

        # Background dropdown — tidak perlu ngetik (Pak Felix)
        background = st.selectbox(
            "🖼️ Background / Environment",
            list(BACKGROUND_OPTIONS.keys()),
            help="Pilih latar belakang gambar iklan"
        )

        # Subjek dropdown — tidak perlu ngetik (Pak Felix)
        subjek = st.selectbox(
            "👤 Subjek dalam Gambar",
            SUBJEK_OPTIONS,
            help="Siapa yang ada di gambar iklan?"
        )

    st.markdown("<br>", unsafe_allow_html=True)
    btn_generate = st.button(
        "🚀 GENERATE IKLAN",
        type="primary",
        use_container_width=True,
        disabled=not VERTEX_CONNECTION_SUCCESS
    )

# =========================================================
# KOLOM KANAN — OUTPUT
# =========================================================
with col_result:
    st.markdown('<div class="step-label">📱 Langkah 4: Hasil Teks Iklan</div>', unsafe_allow_html=True)

    # GENERATE
    if btn_generate:
        if not nama_produk:
            st.warning("⚠️ Isi Nama Produk terlebih dahulu.")
        elif not keywords_list:
            st.warning("⚠️ Isi minimal 1 keyword USP produk.")
        else:
            st.session_state.image_result_final = None
            st.session_state.ai_review_result = None
            st.session_state.chat_history = []

            with st.spinner("🧠 Agen AI menganalisis keyword & referensi visual..."):
                images_data = [img.getvalue() for img in product_images] if product_images else []
                raw_res = generate_ad_text_agentic(
                    kategori, nama_produk, keywords_list, gaya, platform,
                    target_market, mood_visual, background, subjek,
                    images_data, elemen_wajib
                )
                vis_prompt, main_txt = parse_output_for_image(raw_res)
                st.session_state.main_text_result = main_txt
                st.session_state.visual_prompt_result = vis_prompt
                # Increment version → Langkah 5 editor fresh
                st.session_state.visual_prompt_version += 1

            st.session_state.last_params = {
                "kategori": kategori,
                "nama_produk": nama_produk,
                "keywords_list": keywords_list,
                "gaya": gaya,
                "platform": platform,
                "market": target_market,
                "mood": mood_visual,
                "background": background,
                "subjek": subjek,
                "images_data": [img.getvalue() for img in product_images] if product_images else [],
                "elemen_wajib": elemen_wajib,
            }

    # TAMPILKAN HASIL TEKS (LANGKAH 4)
    if st.session_state.main_text_result:
        with st.container(border=True):
            st.markdown(st.session_state.main_text_result)
            st.divider()

            # AI Expert Reviewer (Pak Felix)
            if st.button("🤖 Minta Penilaian AI Expert Reviewer", use_container_width=True):
                with st.spinner("Juri AI mengevaluasi kualitas iklan..."):
                    p = st.session_state.last_params
                    st.session_state.ai_review_result = evaluate_ad_quality(
                        p.get("nama_produk", nama_produk),
                        p.get("keywords_list", keywords_list),
                        p.get("market", target_market),
                        p.get("platform", platform),
                        p.get("elemen_wajib", elemen_wajib),
                        st.session_state.main_text_result
                    )

        if st.session_state.ai_review_result:
            with st.container(border=True):
                st.markdown(st.session_state.ai_review_result)

        # -----------------------------------------------------------
        # LANGKAH 5: EDIT PROMPT VISUAL SEBELUM RENDER
        # FIX BUG: Gunakan key unik berbasis version.
        # Setiap kali Langkah 6 (chatbot) mengubah visual_prompt_result,
        # version di-increment → widget text_area PASTI fresh dengan value terbaru.
        # -----------------------------------------------------------
        st.divider()
        st.markdown('<div class="step-label">🎨 Langkah 5: Pra-Render — Edit Prompt Visual</div>', unsafe_allow_html=True)
        st.caption(
            "AI merumuskan prompt gambar di bawah. "
            "Edit atau tambahkan detail sebelum dirender Imagen 3. "
            "⚡ Prompt ini otomatis diperbarui setelah revisi di Langkah 6."
        )

        # Key unik per version → widget selalu fresh setelah generate/revisi
        editor_key = f"visual_editor_v{st.session_state.visual_prompt_version}"
        edited_visual_prompt = st.text_area(
            "Instruksi ke Imagen 3 (Editable — Bahasa Inggris):",
            value=st.session_state.visual_prompt_result or "",
            height=90,
            key=editor_key
        )

        # TEXT OVERLAY — Tambahan Pak Felix (image bisa ditambah teks/tulisan pendek)
        with st.expander("✏️ Tambahkan Teks/Tulisan ke Gambar (Opsional)"):
            st.caption("Misal: nama produk, harga, tagline. Maks 35 karakter agar tidak berantakan.")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                teks_overlay = st.text_input(
                    "Teks yang ditambahkan",
                    placeholder="Contoh: Rp 15.000 / porsi",
                    max_chars=35
                )
                posisi_teks = st.selectbox(
                    "Posisi Teks",
                    ["Tengah Bawah", "Tengah Atas", "Kiri Atas", "Kanan Bawah", "Tengah"]
                )
            with col_t2:
                ukuran_font = st.slider("Ukuran Font", 24, 96, 48, step=8)
                warna_teks = st.selectbox(
                    "Warna Teks",
                    ["⬜ Putih", "🟡 Kuning", "🟠 Oranye", "⬛ Hitam", "🔴 Merah"]
                )

        if edited_visual_prompt:
            if st.button(
                "✨ RENDER GAMBAR (Imagen 3) + TEMPEL LOGO",
                type="primary",
                use_container_width=True
            ):
                with st.spinner("Memproses gambar resolusi tinggi dengan Imagen 3..."):
                    img_raw_bytes = generate_imagen_image(edited_visual_prompt)

                if img_raw_bytes:
                    current_img = img_raw_bytes

                    if logo_umkm:
                        with st.spinner(f"Menempel logo di posisi {posisi_logo}..."):
                            current_img = apply_dynamic_branding(current_img, logo_umkm, posisi_logo)

                    if teks_overlay.strip():
                        with st.spinner("Menambahkan teks ke gambar..."):
                            current_img = add_text_overlay(
                                current_img, teks_overlay, posisi_teks, ukuran_font, warna_teks
                            )

                    st.session_state.image_result_final = current_img
                    st.balloons()
                else:
                    st.error("Gagal menghasilkan gambar. Coba ulangi.")

    # TAMPILKAN HASIL GAMBAR
    if st.session_state.image_result_final:
        with st.container(border=True):
            st.markdown("#### 🖼️ Hasil Visual Final (Imagen 3 + Logo + Teks)")
            col_pad1, col_img, col_pad2 = st.columns([0.4, 3, 0.4])
            with col_img:
                label_nama = st.session_state.last_params.get("nama_produk", "produk")
                st.image(
                    st.session_state.image_result_final,
                    use_container_width=True,
                    caption=f"Visual iklan profesional — {label_nama}"
                )
                st.download_button(
                    label="⬇️ Download Visual Final (PNG)",
                    data=st.session_state.image_result_final,
                    file_name=f"iklan_{label_nama.replace(' ', '_').lower()}.png",
                    mime="image/png",
                    use_container_width=True
                )

    # PLACEHOLDER
    if not st.session_state.main_text_result:
        with st.container(border=True):
            st.info("👈 Isi form di panel kiri, lalu klik 'GENERATE IKLAN' untuk memulai.")

    # =========================================================
    # LANGKAH 6: CHATBOT REVISI
    # FIX BUG: Setelah revisi, visual_prompt_version di-increment
    # → Langkah 5 text_area otomatis refresh dengan prompt terbaru.
    # =========================================================
    if st.session_state.main_text_result:
        st.divider()
        st.markdown('<div class="step-label">🤖 Langkah 6: Asisten Revisi Cepat</div>', unsafe_allow_html=True)
        st.caption(
            "Kurang puas? Ketik instruksi revisi. AI memperbarui teks iklan "
            "**dan** prompt visual di Langkah 5 secara otomatis. "
            "Contoh: *'Caption lebih pendek'*, *'Tambahkan promo diskon 20%'*, "
            "*'Ganti background jadi lebih gelap'*"
        )

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        revisi_input = st.chat_input("Ketik instruksi revisi di sini...")

        if revisi_input and st.session_state.last_params:
            st.session_state.chat_history.append({"role": "user", "content": revisi_input})

            p = st.session_state.last_params

            with st.spinner("🧠 Gemini Pro merevisi iklan..."):
                new_raw = generate_ad_revision(
                    p["kategori"], p["nama_produk"], p["keywords_list"],
                    p["gaya"], p["platform"], p["market"],
                    p["mood"], p["background"], p["subjek"],
                    p["images_data"], p["elemen_wajib"],
                    instruksi_revisi=revisi_input,
                    teks_sebelumnya=st.session_state.main_text_result
                )

            new_vis_prompt, new_main_txt = parse_output_for_image(new_raw)

            # Update teks iklan
            st.session_state.main_text_result = new_main_txt
            # Update prompt visual + increment version → Langkah 5 auto-refresh
            st.session_state.visual_prompt_result = new_vis_prompt
            st.session_state.visual_prompt_version += 1

            # Reset gambar lama
            st.session_state.image_result_final = None
            st.session_state.ai_review_result = None

            confirm_msg = (
                "✅ Revisi selesai! Teks iklan & prompt visual di **Langkah 5** "
                "sudah diperbarui. Klik **Render Gambar** untuk memperbarui visual."
            )
            st.session_state.chat_history.append({"role": "assistant", "content": confirm_msg})

            st.rerun()
