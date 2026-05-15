import os
import streamlit as st
import re
import io
import base64
from pathlib import Path
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
# MASTER PROMPT LOADER
# ==============================================================================
MASTER_PROMPT_PATH = Path(__file__).parent / "master_prompt_inamikro.md"

def load_master_prompt():
    """Baca master prompt dari file. Fallback minimal jika tidak ada."""
    try:
        if MASTER_PROMPT_PATH.exists():
            return MASTER_PROMPT_PATH.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Gagal baca master prompt: {e}")
    return """Kamu adalah Agen Pakar Marketing Digital UMKM Indonesia.
Buat iklan sesuai input pengguna, ikuti format output per platform."""

MASTER_PROMPT_FULL = load_master_prompt()

# ==============================================================================
# DATA KATEGORI KBLI INAMIKRO
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

BROSUR_ELEMEN = {
    "food": ["Nama Produk", "Harga", "Keunggulan/USP", "Promo/Diskon (jika ada)", "Call-to-Action", "Kontak/WhatsApp"],
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
    "🧱 Bata Industrial": "industrial brick wall background with warm lighting",
    "🌸 Pastel Aesthetic": "soft pastel pink and cream aesthetic background",
    "🎋 Bambu / Tradisional": "bamboo mat traditional Indonesian background",
    "✨ Gradient Premium": "smooth dark gradient luxury background with golden accent",
}

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

# Preset teks promo brosur (Tambahan Pak Greg: brosur digital siap cetak)
PRESET_BROSUR = {
    "(Custom — ketik sendiri)": "",
    "🔥 Promo Bulan Ini": "PROMO BULAN INI",
    "💰 Diskon 50%": "DISKON 50%",
    "🎉 Buy 1 Get 1": "BUY 1 GET 1",
    "🆕 Menu Baru": "MENU BARU",
    "⭐ Best Seller": "BEST SELLER",
    "🛵 Free Ongkir": "FREE ONGKIR",
    "🔖 Mulai Rp 10.000": "MULAI Rp 10.000",
    "📞 Pesan via WA": "ORDER VIA WHATSAPP",
}

# ==============================================================================
# BAGIAN 2: ENGINE AI (MASTER PROMPT-DRIVEN)
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
    """Generate gambar dengan Imagen 3."""
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
    llm_generator = ChatVertexAI(
        model_name="gemini-2.5-pro",
        temperature=0.3,
        max_output_tokens=8192
    )
    llm_evaluator = ChatVertexAI(
        model_name="gemini-2.5-pro",
        temperature=0.1,
        max_output_tokens=4096
    )
    llm_cross_evaluator = ChatVertexAI(
        model_name="gemini-2.5-flash",
        temperature=0.1,
        max_output_tokens=4096
    )
except Exception:
    pass


def build_context_block(kategori, nama_produk, keywords_list, gaya, platform,
                        market, mood, background, subjek, elemen_wajib,
                        photo_descriptions=None):
    """
    Bangun blok konteks input terstruktur.
    photo_descriptions: list keterangan untuk setiap foto referensi (Revisi Pak Greg).
    """
    market_str = ", ".join(market) if market else "Umum"
    keywords_str = ", ".join(keywords_list) if keywords_list else nama_produk
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])
    bg_desc = BACKGROUND_OPTIONS.get(background, background)

    photo_block = ""
    if photo_descriptions:
        photo_lines = []
        for i, desc in enumerate(photo_descriptions, 1):
            label = desc.strip() if desc and desc.strip() else "(tidak ada keterangan)"
            photo_lines.append(f"  - Foto {i}: {label}")
        photo_block = f"\nKETERANGAN FOTO REFERENSI (penting untuk replikasi visual):\n" + "\n".join(photo_lines)

    return f"""
=== INPUT TERSTRUKTUR (dari pengguna saat ini) ===
LANGKAH 1 — BRANDING:
- Target Market: {market_str}

LANGKAH 2 — PRODUK:
- Nama Produk: {nama_produk}
- Keyword USP: {keywords_str}
- Kategori KBLI: {kategori}
- Tipe UMKM: {KBLI_DATA.get(kategori, {}).get('tipe', 'food')}{photo_block}

LANGKAH 3 — STRATEGI:
- Platform: {platform}
- Tone of Voice: {gaya}
- Mood Visual: {mood}
- Background: {bg_desc}
- Subjek Gambar: {subjek}

ELEMEN WAJIB BROSUR (untuk kategori ini):
{elemen_str}
"""


def build_visual_fidelity_instruction(photo_descriptions):
    """
    Instruksi tambahan agar AI replikasi bentuk produk asli (Revisi Pak Greg).
    "Jangan sampai bedanya jauh banget dengan produk asli."
    """
    if not photo_descriptions:
        return ""

    described = [d.strip() for d in photo_descriptions if d and d.strip()]
    if not described:
        described_block = "produk yang ada di foto referensi"
    else:
        described_block = ", ".join(described)

    return f"""

=== ATURAN VISUAL FIDELITY (KETAT — dari Pak Greg) ===
- Foto referensi yang diunggah pengguna BERISI: {described_block}
- Ide Visual HARUS mereplikasi BENTUK, WARNA, KEMASAN produk dari foto referensi tersebut.
- DILARANG mengarang produk yang tidak ada di foto referensi.
- DILARANG mengganti produk dengan produk lain (misal: foto Bakwan jangan jadi Donat).
- Yang BOLEH dimanipulasi hanya: background, pencahayaan, subjek pendukung, mood, sudut pandang.
- Komposisi produk harus IDENTIK dengan foto asli, hanya disajikan dalam kualitas iklan profesional.
"""


@st.cache_data(show_spinner=False)
def generate_ad_text_master(
    kategori, nama_produk, keywords_list, gaya, platform,
    market, mood, background, subjek, images_bytes_list,
    elemen_wajib, photo_descriptions=None
):
    """Generate iklan dengan Master Prompt + visual fidelity rule."""
    context_block = build_context_block(
        kategori, nama_produk, keywords_list, gaya, platform,
        market, mood, background, subjek, elemen_wajib, photo_descriptions
    )
    fidelity_block = build_visual_fidelity_instruction(photo_descriptions) if images_bytes_list else ""

    full_prompt = f"""{MASTER_PROMPT_FULL}

---

{context_block}
{fidelity_block}

=== TUGAS SEKARANG ===
Eksekusi **LANGKAH 4 (Generate Konten Iklan)** dari master prompt di atas,
menggunakan data input terstruktur yang telah diberikan.

Output HARUS mengikuti format WAJIB untuk platform {platform} sesuai master prompt.
DILARANG basa-basi. Langsung keluarkan output.
"""

    content_parts = [{"type": "text", "text": full_prompt}]
    for img_bytes in images_bytes_list:
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    return llm_generator.invoke([HumanMessage(content=content_parts)]).content


@st.cache_data(show_spinner=False)
def generate_ad_revision_master(
    kategori, nama_produk, keywords_list, gaya, platform,
    market, mood, background, subjek, images_bytes_list,
    elemen_wajib, instruksi_revisi, teks_sebelumnya, photo_descriptions=None
):
    """Revisi iklan (Chatbot Mode) dengan Master Prompt."""
    context_block = build_context_block(
        kategori, nama_produk, keywords_list, gaya, platform,
        market, mood, background, subjek, elemen_wajib, photo_descriptions
    )
    fidelity_block = build_visual_fidelity_instruction(photo_descriptions) if images_bytes_list else ""

    revisi_prompt = f"""{MASTER_PROMPT_FULL}

---

{context_block}
{fidelity_block}

=== HASIL IKLAN SEBELUMNYA ===
{teks_sebelumnya}

=== INSTRUKSI REVISI DARI USER ===
{instruksi_revisi}

=== TUGAS SEKARANG ===
Eksekusi **ALUR REVISI (CHATBOT MODE)** dari master prompt di atas.
Revisi iklan sesuai permintaan user, pertahankan format asli.
WAJIB: bagian **Ide Visual** di paling bawah HARUS tetap ada dan diperbarui
jika revisi menyangkut visual.
"""

    content_parts = [{"type": "text", "text": revisi_prompt}]
    for img_bytes in images_bytes_list:
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    return llm_generator.invoke([HumanMessage(content=content_parts)]).content


def build_evaluation_prompt(nama_produk, keywords_list, target_market, platform,
                            elemen_wajib, generated_ad, evaluator_label="Gemini Pro"):
    keywords_str = ", ".join(keywords_list) if keywords_list else nama_produk
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])
    market_str = ", ".join(target_market) if target_market else "Umum"

    return f"""ANDA ADALAH JURI PAKAR DIGITAL MARKETING INDONESIA YANG NETRAL DAN OBJEKTIF.
ANDA BUKAN AGEN YANG MEMBUAT IKLAN INI. Anda evaluator independen.

Evaluator ID: {evaluator_label}

=== REQUIREMENT (Prompt Input dari User) ===
- Nama Produk: {nama_produk}
- Keyword USP: {keywords_str}
- Target Market: {market_str}
- Platform: {platform}
- Elemen Wajib Brosur:
{elemen_str}

=== HASIL IKLAN YANG DIEVALUASI ===
{generated_ad}

=== KRITERIA EVALUASI (masing-masing 0-25 poin) ===
1. RELEVANSI PRODUK: Sesuai dengan nama produk & keyword USP?
2. KESESUAIAN TARGET MARKET: Gaya bahasa & konten cocok untuk target {market_str}?
3. KELENGKAPAN ELEMEN WAJIB: Berapa dari {len(elemen_wajib)} elemen wajib yang terpenuhi?
4. KUALITAS COPYWRITING: Seberapa menarik, persuasif, dan profesional?

FORMAT OUTPUT WAJIB:
**📊 Hasil Evaluasi — {evaluator_label}:**

| Kriteria | Skor | Catatan |
|---|---|---|
| Relevansi Produk | X/25 | [catatan singkat] |
| Kesesuaian Target Market | X/25 | [catatan singkat] |
| Kelengkapan Elemen Wajib | X/25 | [catatan singkat] |
| Kualitas Copywriting | X/25 | [catatan singkat] |
| **TOTAL SKOR** | **XX/100** | **XX%** |

**✅ Kekuatan Utama:** [1 kalimat]
**⚠️ Rekomendasi Perbaikan:** [1-2 kalimat konkret]
"""


@st.cache_data(show_spinner=False)
def evaluate_ad_quality_dual(nama_produk, keywords_list, target_market, platform,
                              elemen_wajib, generated_ad):
    """Dual AI Expert Review — sesuai arahan Pak Felix (cross-AI validation)."""
    prompt_pro = build_evaluation_prompt(
        nama_produk, keywords_list, target_market, platform,
        elemen_wajib, generated_ad, evaluator_label="Juri A — Gemini 2.5 Pro"
    )
    prompt_flash = build_evaluation_prompt(
        nama_produk, keywords_list, target_market, platform,
        elemen_wajib, generated_ad, evaluator_label="Juri B — Gemini 2.5 Flash"
    )

    try:
        hasil_pro = llm_evaluator.invoke(prompt_pro).content
    except Exception as e:
        hasil_pro = f"Gagal eksekusi Juri A: {e}"

    try:
        hasil_flash = llm_cross_evaluator.invoke(prompt_flash).content
    except Exception as e:
        hasil_flash = f"Gagal eksekusi Juri B: {e}"

    return hasil_pro, hasil_flash


def extract_total_score(review_text):
    try:
        m = re.search(r"\*\*TOTAL SKOR\*\*\s*\|\s*\*\*(\d+)/100", review_text)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


# ==============================================================================
# BAGIAN 3: MANIPULASI GAMBAR — LOGO + TEXT OVERLAY
# ==============================================================================

def apply_dynamic_branding(main_image_bytes, logo_file_uploaded, posisi):
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


def add_text_overlay(main_image_bytes, teks_overlay, posisi_teks, ukuran_font, warna_teks, dengan_kotak=False):
    """
    Tambahkan teks/tulisan ke gambar (revisi Pak Greg: bisa untuk brosur cetak).
    dengan_kotak: tambahkan background kotak di belakang teks agar lebih kontras.
    """
    if not main_image_bytes or not teks_overlay.strip():
        return main_image_bytes
    try:
        main_img = Image.open(io.BytesIO(main_image_bytes)).convert("RGBA")
        main_w, main_h = main_img.size

        txt_layer = Image.new("RGBA", main_img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        # Cari font yang tersedia
        font = None
        for font_name in ["arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]:
            try:
                font = ImageFont.truetype(font_name, ukuran_font)
                break
            except Exception:
                continue
        if font is None:
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
            pos = ((main_w - teks_w) // 2, main_h - teks_h - padding * 2)
        elif posisi_teks == "Kiri Atas":
            pos = (padding, padding)
        elif posisi_teks == "Kanan Bawah":
            pos = (main_w - teks_w - padding, main_h - teks_h - padding * 2)
        else:
            pos = ((main_w - teks_w) // 2, (main_h - teks_h) // 2)

        color_map = {
            "⬜ Putih": (255, 255, 255, 240),
            "🟡 Kuning": (255, 220, 0, 240),
            "🟠 Oranye": (255, 120, 0, 240),
            "⬛ Hitam": (20, 20, 20, 240),
            "🔴 Merah": (220, 30, 30, 240),
        }
        fill_color = color_map.get(warna_teks, (255, 255, 255, 240))

        # Kotak background untuk brosur (opsional)
        if dengan_kotak:
            box_padding = max(15, ukuran_font // 4)
            box_x1 = pos[0] - box_padding
            box_y1 = pos[1] - box_padding // 2
            box_x2 = pos[0] + teks_w + box_padding
            box_y2 = pos[1] + teks_h + box_padding
            # Kotak warna kontras dengan teks
            if warna_teks in ["⬜ Putih", "🟡 Kuning"]:
                box_color = (0, 0, 0, 200)
            else:
                box_color = (255, 255, 255, 220)
            draw.rectangle([box_x1, box_y1, box_x2, box_y2], fill=box_color)

        # Shadow untuk keterbacaan
        shadow_offset = max(2, ukuran_font // 20)
        draw.text(
            (pos[0] + shadow_offset, pos[1] + shadow_offset),
            teks_overlay, font=font, fill=(0, 0, 0, 180)
        )
        draw.text(pos, teks_overlay, font=font, fill=fill_color)

        result = Image.alpha_composite(main_img, txt_layer).convert("RGB")
        img_byte_arr = io.BytesIO()
        result.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception as e:
        st.error(f"Gagal tambah teks: {e}")
        return main_image_bytes


# ==============================================================================
# BAGIAN 4: UI/UX STREAMLIT — V8 FINAL
# ==============================================================================

st.set_page_config(
    page_title="Inamikro Ad Generator V8",
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
    .master-prompt-badge {
        background:#ede7f6; border-radius:4px;
        padding:0.3rem 0.6rem; font-size:0.78rem; color:#4527a0;
        display:inline-block; margin-bottom:0.5rem;
    }
    .photo-caption-box {
        background: #fff3e0; border-left: 3px solid #fb8c00;
        border-radius: 4px; padding: 0.3rem 0.6rem;
        font-size: 0.78rem; color: #444; margin-top: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>📈 Inamikro Ad Generator</h1>
    <p>Platform Konten Iklan UMKM Berbasis Agentic AI — Gemini 2.5 Pro & Imagen 3 &nbsp;|&nbsp; Versi 8</p>
</div>
""", unsafe_allow_html=True)

col_badge1, col_badge2 = st.columns([3, 1])
with col_badge1:
    mp_status = "✅ Master Prompt aktif" if MASTER_PROMPT_PATH.exists() else "⚠️ Master Prompt fallback"
    st.markdown(f'<div class="master-prompt-badge">🧠 {mp_status} | <code>master_prompt_inamikro.md</code></div>', unsafe_allow_html=True)
with col_badge2:
    with st.popover("📄 Lihat Master Prompt"):
        st.markdown(MASTER_PROMPT_FULL[:3000] + ("\n\n...*(dipotong)*" if len(MASTER_PROMPT_FULL) > 3000 else ""))

st.divider()

if not VERTEX_CONNECTION_SUCCESS:
    st.error(
        "⚠️ Sistem Offline. Jalankan: "
        "`gcloud auth application-default login --project=careful-ensign-477104-p5`"
    )

# --- SESSION STATE ---
defaults = {
    'main_text_result': None,
    'visual_prompt_result': None,
    'image_result_final': None,
    'ai_review_pro': None,
    'ai_review_flash': None,
    'score_pro': None,
    'score_flash': None,
    'chat_history': [],
    'last_params': {},
    'visual_prompt_version': 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

col_form, col_result = st.columns([1, 1.45], gap="large")

# =========================================================
# KOLOM KIRI — FORM
# =========================================================
with col_form:

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
                st.image(logo_umkm, width=70, caption="Preview")
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
            default=["Umum"]
        )

    st.markdown('<div class="step-label">📝 Langkah 2: Data Produk & Referensi Visual</div>', unsafe_allow_html=True)
    with st.container(border=True):
        nama_produk = st.text_input("Nama Produk / Brand", placeholder="Contoh: Bakwan Sowan")

        st.markdown(
            '<div class="info-note">💡 Isi kata kunci keunggulan produk, pisahkan dengan koma.</div>',
            unsafe_allow_html=True
        )
        keywords_raw = st.text_input(
            "Keyword USP Produk",
            placeholder="Contoh: keju creamy, siomay nori, halal, harga terjangkau"
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

        # ============ TAMBAHAN PAK GREG ============
        # Foto referensi + keterangan per foto agar AI tidak salah identifikasi
        product_images = st.file_uploader(
            "📷 Upload Foto Produk (kalau ada — biar AI hasilnya sangat mirip produk asli)",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            help="Tidak wajib, tapi sangat membantu agar gambar AI mirip produk asli Anda"
        )

        # Keterangan per foto (Revisi Pak Greg)
        photo_descriptions = []
        if product_images:
            st.markdown(
                '<div class="photo-caption-box">'
                '🏷️ <b>Beri keterangan singkat tiap foto</b> (Pak Greg: '
                'agar AI tahu mana produk utama mana camilan tambahan)'
                '</div>',
                unsafe_allow_html=True
            )
            for idx, img_file in enumerate(product_images[:5]):
                cap_col1, cap_col2 = st.columns([1, 2.5])
                with cap_col1:
                    st.image(img_file, use_container_width=True, caption=f"Foto {idx+1}")
                with cap_col2:
                    desc = st.text_input(
                        f"Keterangan Foto {idx+1}",
                        key=f"photo_desc_{idx}",
                        placeholder="Contoh: Bakwan keju (produk utama)",
                        label_visibility="collapsed"
                    )
                    photo_descriptions.append(desc)

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

        background = st.selectbox("🖼️ Background / Environment", list(BACKGROUND_OPTIONS.keys()))
        subjek = st.selectbox("👤 Subjek dalam Gambar", SUBJEK_OPTIONS)

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

    if btn_generate:
        if not nama_produk:
            st.warning("⚠️ Isi Nama Produk terlebih dahulu.")
        elif not keywords_list:
            st.warning("⚠️ Isi minimal 1 keyword USP produk.")
        else:
            st.session_state.image_result_final = None
            st.session_state.ai_review_pro = None
            st.session_state.ai_review_flash = None
            st.session_state.score_pro = None
            st.session_state.score_flash = None
            st.session_state.chat_history = []

            with st.spinner("🧠 Agen AI memuat Master Prompt & menganalisis input..."):
                images_data = [img.getvalue() for img in product_images] if product_images else []
                raw_res = generate_ad_text_master(
                    kategori, nama_produk, keywords_list, gaya, platform,
                    target_market, mood_visual, background, subjek,
                    images_data, elemen_wajib,
                    photo_descriptions=photo_descriptions
                )
                vis_prompt, main_txt = parse_output_for_image(raw_res)
                st.session_state.main_text_result = main_txt
                st.session_state.visual_prompt_result = vis_prompt
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
                "photo_descriptions": photo_descriptions,
            }

    if st.session_state.main_text_result:
        with st.container(border=True):
            st.markdown(st.session_state.main_text_result)
            st.divider()

            col_ev_btn, col_ev_info = st.columns([1.3, 1])
            with col_ev_btn:
                if st.button("🤖 Minta Penilaian 2 AI Evaluator (Dual Review)", use_container_width=True):
                    with st.spinner("Dua juri AI mengevaluasi (Gemini Pro + Flash)..."):
                        p = st.session_state.last_params
                        hasil_pro, hasil_flash = evaluate_ad_quality_dual(
                            p.get("nama_produk", nama_produk),
                            p.get("keywords_list", keywords_list),
                            p.get("market", target_market),
                            p.get("platform", platform),
                            p.get("elemen_wajib", elemen_wajib),
                            st.session_state.main_text_result
                        )
                        st.session_state.ai_review_pro = hasil_pro
                        st.session_state.ai_review_flash = hasil_flash
                        st.session_state.score_pro = extract_total_score(hasil_pro)
                        st.session_state.score_flash = extract_total_score(hasil_flash)
            with col_ev_info:
                st.caption("ℹ️ 2 model AI berbeda = cross-validation, mengurangi bias.")

        if st.session_state.ai_review_pro or st.session_state.ai_review_flash:
            if st.session_state.score_pro is not None and st.session_state.score_flash is not None:
                skor_avg = (st.session_state.score_pro + st.session_state.score_flash) / 2
                selisih = abs(st.session_state.score_pro - st.session_state.score_flash)
                with st.container(border=True):
                    st.markdown("#### 📊 Ringkasan Komparasi Skor (Cross-AI Validation)")
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    with col_m1:
                        st.metric("Juri A (Pro)", f"{st.session_state.score_pro}/100")
                    with col_m2:
                        st.metric("Juri B (Flash)", f"{st.session_state.score_flash}/100")
                    with col_m3:
                        st.metric("Rata-rata", f"{skor_avg:.1f}/100")
                    with col_m4:
                        reliabilitas = "Tinggi" if selisih <= 10 else ("Sedang" if selisih <= 20 else "Rendah")
                        st.metric("Reliabilitas", reliabilitas, f"Selisih: {selisih}")

            col_rev1, col_rev2 = st.columns(2)
            with col_rev1:
                if st.session_state.ai_review_pro:
                    with st.container(border=True):
                        st.markdown(st.session_state.ai_review_pro)
            with col_rev2:
                if st.session_state.ai_review_flash:
                    with st.container(border=True):
                        st.markdown(st.session_state.ai_review_flash)

        # -----------------------------------------------------------
        # LANGKAH 5: PRA-RENDER + BROSUR DIGITAL
        # -----------------------------------------------------------
        st.divider()
        st.markdown('<div class="step-label">🎨 Langkah 5: Pra-Render Gambar & Brosur Digital</div>', unsafe_allow_html=True)
        st.caption(
            "Edit prompt visual sebelum render. "
            "⚡ Otomatis update setelah revisi di Langkah 6."
        )

        editor_key = f"visual_editor_v{st.session_state.visual_prompt_version}"
        edited_visual_prompt = st.text_area(
            "Instruksi ke Imagen 3 (Editable — Bahasa Inggris):",
            value=st.session_state.visual_prompt_result or "",
            height=90,
            key=editor_key
        )

        # ============ TAMBAHAN PAK GREG: BROSUR DIGITAL ============
        with st.expander("✏️ Tambahkan Teks Brosur ke Gambar (Untuk Promo / Cetak)", expanded=False):
            st.caption(
                "💡 \"Tambah tulisan promo langsung di atas gambar, "
                "biar bisa langsung cetak atau posting.\""
            )

            preset_brosur = st.selectbox(
                "Preset Cepat",
                list(PRESET_BROSUR.keys()),
                help="Pilih preset atau ketik sendiri"
            )

            default_text = PRESET_BROSUR.get(preset_brosur, "")
            teks_overlay = st.text_input(
                "Teks Brosur",
                value=default_text,
                placeholder="Contoh: ALL ITEM 50RB",
                max_chars=40,
                key=f"brosur_text_{preset_brosur}"
            )

            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                posisi_teks = st.selectbox(
                    "Posisi",
                    ["Tengah Bawah", "Tengah Atas", "Kiri Atas", "Kanan Bawah", "Tengah"]
                )
            with col_t2:
                ukuran_font = st.slider("Ukuran Font", 24, 120, 64, step=8)
            with col_t3:
                warna_teks = st.selectbox(
                    "Warna",
                    ["⬜ Putih", "🟡 Kuning", "🟠 Oranye", "⬛ Hitam", "🔴 Merah"]
                )

            dengan_kotak = st.checkbox(
                "🔲 Tambahkan kotak background (lebih kontras, cocok untuk brosur)",
                value=False
            )

        if edited_visual_prompt:
            if st.button(
                "✨ RENDER GAMBAR (Imagen 3) + LOGO + TEKS BROSUR",
                type="primary",
                use_container_width=True
            ):
                with st.spinner("Memproses gambar resolusi tinggi dengan Imagen 3..."):
                    img_raw_bytes = generate_imagen_image(edited_visual_prompt)

                if img_raw_bytes:
                    current_img = img_raw_bytes
                    if logo_umkm:
                        with st.spinner(f"Menempel logo di {posisi_logo}..."):
                            current_img = apply_dynamic_branding(current_img, logo_umkm, posisi_logo)
                    if teks_overlay.strip():
                        with st.spinner("Menambahkan teks brosur ke gambar..."):
                            current_img = add_text_overlay(
                                current_img, teks_overlay, posisi_teks,
                                ukuran_font, warna_teks, dengan_kotak
                            )
                    st.session_state.image_result_final = current_img
                    st.balloons()
                else:
                    st.error("Gagal menghasilkan gambar. Coba ulangi.")

    if st.session_state.image_result_final:
        with st.container(border=True):
            st.markdown("#### 🖼️ Hasil Visual Final (Brosur Digital)")
            col_pad1, col_img, col_pad2 = st.columns([0.4, 3, 0.4])
            with col_img:
                label_nama = st.session_state.last_params.get("nama_produk", "produk")
                st.image(
                    st.session_state.image_result_final,
                    use_container_width=True,
                    caption=f"Brosur digital — {label_nama}"
                )
                st.download_button(
                    label="⬇️ Download Brosur (PNG, siap cetak/posting)",
                    data=st.session_state.image_result_final,
                    file_name=f"brosur_{label_nama.replace(' ', '_').lower()}.png",
                    mime="image/png",
                    use_container_width=True
                )

    if not st.session_state.main_text_result:
        with st.container(border=True):
            st.info("👈 Isi form di panel kiri, lalu klik 'GENERATE IKLAN' untuk memulai.")

    # =========================================================
    # LANGKAH 6: CHATBOT REVISI
    # =========================================================
    if st.session_state.main_text_result:
        st.divider()
        st.markdown('<div class="step-label">🤖 Langkah 6: Asisten Revisi Cepat</div>', unsafe_allow_html=True)
        st.caption("Kurang puas? Ketik instruksi revisi. AI memperbarui teks **dan** prompt visual.")

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        revisi_input = st.chat_input("Ketik instruksi revisi di sini...")

        if revisi_input and st.session_state.last_params:
            st.session_state.chat_history.append({"role": "user", "content": revisi_input})
            p = st.session_state.last_params

            with st.spinner("🧠 Gemini Pro merevisi berdasarkan Master Prompt..."):
                new_raw = generate_ad_revision_master(
                    p["kategori"], p["nama_produk"], p["keywords_list"],
                    p["gaya"], p["platform"], p["market"],
                    p["mood"], p["background"], p["subjek"],
                    p["images_data"], p["elemen_wajib"],
                    instruksi_revisi=revisi_input,
                    teks_sebelumnya=st.session_state.main_text_result,
                    photo_descriptions=p.get("photo_descriptions", [])
                )

            new_vis_prompt, new_main_txt = parse_output_for_image(new_raw)

            st.session_state.main_text_result = new_main_txt
            st.session_state.visual_prompt_result = new_vis_prompt
            st.session_state.visual_prompt_version += 1
            st.session_state.image_result_final = None
            st.session_state.ai_review_pro = None
            st.session_state.ai_review_flash = None
            st.session_state.score_pro = None
            st.session_state.score_flash = None

            confirm_msg = (
                "✅ Revisi selesai! Teks iklan & prompt visual di **Langkah 5** "
                "sudah diperbarui. Klik **Render Gambar** untuk memperbarui visual."
            )
            st.session_state.chat_history.append({"role": "assistant", "content": confirm_msg})
            st.rerun()
