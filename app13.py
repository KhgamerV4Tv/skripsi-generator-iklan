import os
import streamlit as st
import re
import io
import base64
import requests
import openai
from pathlib import Path
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import google.generativeai as genai

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
        vertexai.init(
            project=YOUR_PROJECT_ID,
            location=YOUR_LOCATION
        )
        VERTEX_CONNECTION_SUCCESS = True

except Exception as e:
    VERTEX_CONNECTION_SUCCESS = False
    print(f"Gagal init Vertex AI: {e}")

# ==============================================================================
# MASTER PROMPT LOADER
# ==============================================================================
MASTER_PROMPT_PATH = Path(__file__).parent / "master_prompt_inamikro.md"

def load_master_prompt():
    """Baca master prompt dari file .md eksternal."""
    try:
        if MASTER_PROMPT_PATH.exists():
            return MASTER_PROMPT_PATH.read_text(encoding="utf-8")

    except Exception as e:
        print(f"Gagal baca master prompt: {e}")

    return """
Kamu adalah Agen Pakar Marketing Digital UMKM Indonesia.
Buat iklan sesuai input pengguna, ikuti format output per platform.
"""

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
        "desc": "Usaha yang menjual minuman dan makanan ringan.",
        "contoh": "Kopi susu, boba, kedai es, kafe",
        "tipe": "food"
    },

    "10794 - Industri Keripik & Makanan Ringan": {
        "desc": "Usaha produksi makanan ringan dalam kemasan.",
        "contoh": "Keripik singkong, makaroni pedas",
        "tipe": "food"
    },

    "10750 - Industri Makanan Olahan (Frozen Food)": {
        "desc": "Usaha makanan beku.",
        "contoh": "Dimsum, nugget, siomay",
        "tipe": "food"
    },

    "47711 - Perdagangan Eceran Pakaian (Fashion)": {
        "desc": "Usaha penjualan pakaian.",
        "contoh": "Kaos distro, gamis",
        "tipe": "fashion"
    },

    "96012 - Jasa Penatu/Laundry": {
        "desc": "Usaha laundry kiloan.",
        "contoh": "Laundry express",
        "tipe": "jasa"
    }
}

KBLI_CATEGORIES = list(KBLI_DATA.keys())

# ==============================================================================
# DATA VISUAL
# ==============================================================================
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
    "Suasana ramai"
]

MOOD_OPTIONS = [
    "Cerah & Ceria",
    "Gelap & Elegan",
    "Minimalis & Clean",
    "Hangat & Estetik",
    "Playful & Colorful"
]

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
# UTIL FUNCTIONS
# ==============================================================================
def parse_output_for_image(markdown_text):

    try:
        matches = list(
            re.finditer(
                r"\*\*Ide Visual:\*\*[\s]*(.*?)(?=\n\n|\Z)",
                markdown_text,
                re.IGNORECASE | re.DOTALL
            )
        )

        if matches:
            last_match = matches[-1]

            clean_idea = (
                last_match.group(1)
                .strip()
                .replace("*", "")
                .replace("\n", " ")
            )

            main_text = markdown_text[:last_match.start()].strip()

            return clean_idea[:500], main_text

    except Exception:
        pass

    return "", markdown_text

# ==============================================================================
# IMAGE GENERATION MODELS
# ==============================================================================

@st.cache_data(show_spinner=False)
def generate_imagen_image(prompt_text):

    if (
        not IS_VERTEX_AVAILABLE
        or not VERTEX_CONNECTION_SUCCESS
        or not prompt_text
    ):
        return None

    full_prompt = (
        f"professional product photography, {prompt_text}, "
        "photorealistic, highly detailed, 8k resolution, "
        "commercial advertisement style, no text overlay, "
        "sharp focus, beautiful cinematic lighting."
    )

    try:
        model = ImageGenerationModel.from_pretrained(
            "imagen-3.0-generate-001"
        )

        response = model.generate_images(
            prompt=full_prompt,
            number_of_images=1,
            aspect_ratio="1:1"
        )

        return response.images[0]._image_bytes

    except Exception as e:
        st.error(f"Gagal generate Imagen 3.0: {e}")
        return None


@st.cache_data(show_spinner=False)
def generate_dalle_image(prompt_text):

    if not prompt_text:
        return None

    full_prompt = (
        f"professional product photography, {prompt_text}, "
        "photorealistic, highly detailed, "
        "commercial advertisement style, no text overlay."
    )

    try:
        client = openai.OpenAI(
            api_key=st.secrets["OPENAI_API_KEY"]
        )

        response = client.images.generate(
            model="gpt-image-2",
            prompt=full_prompt,
            size="1024x1024",
            quality="auto",
            n=1,
            response_format="b64_json"
        )

        image_data = response.data[0]

        # SAFE MODE
        if hasattr(image_data, "b64_json") and image_data.b64_json:
            return base64.b64decode(image_data.b64_json)

        elif hasattr(image_data, "url") and image_data.url:
            return requests.get(image_data.url).content

        st.error("OpenAI tidak mengembalikan data gambar.")
        return None

    except Exception as e:
        st.error(f"Gagal generate GPT Image 2: {e}")
        return None


@st.cache_data(show_spinner=False)
def generate_gemini_flash_image(prompt_text):

    if not prompt_text:
        return None

    full_prompt = (
        f"professional product photography, {prompt_text}, "
        "photorealistic, highly detailed, 8k resolution, "
        "commercial advertisement style, no text overlay, "
        "sharp focus, beautiful cinematic lighting."
    )

    try:
        genai.configure(
            api_key=st.secrets["GEMINI_API_KEY"]
        )

        model = genai.GenerativeModel(
            "models/nano-banana-2"
        )

        response = model.generate_content(full_prompt)

        # Cari image binary
        for candidate in response.candidates:
            for part in candidate.content.parts:

                if hasattr(part, "inline_data") and part.inline_data:
                    return part.inline_data.data

        st.error("Response Gemini tidak mengandung gambar.")
        return None

    except Exception as e:
        st.error(f"Gagal generate Nano Banana 2: {e}")
        return None

# ==============================================================================
# IMAGE MANIPULATION
# ==============================================================================
def apply_dynamic_branding(
    main_image_bytes,
    logo_file_uploaded,
    posisi
):

    if not main_image_bytes or not logo_file_uploaded:
        return main_image_bytes

    try:
        main_img = Image.open(
            io.BytesIO(main_image_bytes)
        )

        logo_img = Image.open(
            logo_file_uploaded
        ).convert("RGBA")

        new_logo_w = int(main_img.width * 0.18)

        new_logo_h = int(
            new_logo_w * (
                logo_img.height / logo_img.width
            )
        )

        logo_img = logo_img.resize(
            (new_logo_w, new_logo_h),
            Image.Resampling.LANCZOS
        )

        alpha = logo_img.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(0.88)
        logo_img.putalpha(alpha)

        padding = 28

        if posisi == "Kanan Atas":
            pos = (
                main_img.width - new_logo_w - padding,
                padding
            )

        elif posisi == "Kiri Atas":
            pos = (padding, padding)

        elif posisi == "Kanan Bawah":
            pos = (
                main_img.width - new_logo_w - padding,
                main_img.height - new_logo_h - padding
            )

        else:
            pos = (
                padding,
                main_img.height - new_logo_h - padding
            )

        branded_img = main_img.copy()
        branded_img.paste(logo_img, pos, logo_img)

        img_byte_arr = io.BytesIO()

        branded_img.save(
            img_byte_arr,
            format="PNG"
        )

        return img_byte_arr.getvalue()

    except Exception as e:
        st.error(f"Gagal tempel logo: {e}")
        return main_image_bytes


def add_text_overlay(
    main_image_bytes,
    teks_overlay,
    posisi_teks,
    ukuran_font,
    warna_teks,
    dengan_kotak=False
):

    if not main_image_bytes or not teks_overlay.strip():
        return main_image_bytes

    try:
        main_img = Image.open(
            io.BytesIO(main_image_bytes)
        ).convert("RGBA")

        txt_layer = Image.new(
            "RGBA",
            main_img.size,
            (255, 255, 255, 0)
        )

        draw = ImageDraw.Draw(txt_layer)

        font = None

        for font_name in [
            "arialbd.ttf",
            "arial.ttf",
            "DejaVuSans-Bold.ttf",
            "DejaVuSans.ttf"
        ]:

            try:
                font = ImageFont.truetype(
                    font_name,
                    ukuran_font
                )
                break

            except Exception:
                continue

        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox(
            (0, 0),
            teks_overlay,
            font=font
        )

        teks_w = bbox[2] - bbox[0]
        teks_h = bbox[3] - bbox[1]

        padding = 30

        if posisi_teks == "Tengah Atas":
            pos = (
                (main_img.width - teks_w) // 2,
                padding
            )

        elif posisi_teks == "Tengah Bawah":
            pos = (
                (main_img.width - teks_w) // 2,
                main_img.height - teks_h - padding * 2
            )

        elif posisi_teks == "Kiri Atas":
            pos = (padding, padding)

        elif posisi_teks == "Kanan Bawah":
            pos = (
                main_img.width - teks_w - padding,
                main_img.height - teks_h - padding * 2
            )

        else:
            pos = (
                (main_img.width - teks_w) // 2,
                (main_img.height - teks_h) // 2
            )

        color_map = {
            "⬜ Putih": (255, 255, 255, 240),
            "🟡 Kuning": (255, 220, 0, 240),
            "🟠 Oranye": (255, 120, 0, 240),
            "⬛ Hitam": (20, 20, 20, 240),
            "🔴 Merah": (220, 30, 30, 240),
        }

        fill_color = color_map.get(
            warna_teks,
            (255, 255, 255, 240)
        )

        if dengan_kotak:

            box_padding = max(
                15,
                ukuran_font // 4
            )

            box_x1 = pos[0] - box_padding
            box_y1 = pos[1] - box_padding // 2

            box_x2 = pos[0] + teks_w + box_padding
            box_y2 = pos[1] + teks_h + box_padding

            box_color = (
                (0, 0, 0, 200)
                if warna_teks in ["⬜ Putih", "🟡 Kuning"]
                else (255, 255, 255, 220)
            )

            draw.rectangle(
                [box_x1, box_y1, box_x2, box_y2],
                fill=box_color
            )

        shadow_offset = max(
            2,
            ukuran_font // 20
        )

        draw.text(
            (
                pos[0] + shadow_offset,
                pos[1] + shadow_offset
            ),
            teks_overlay,
            font=font,
            fill=(0, 0, 0, 180)
        )

        draw.text(
            pos,
            teks_overlay,
            font=font,
            fill=fill_color
        )

        result = Image.alpha_composite(
            main_img,
            txt_layer
        ).convert("RGB")

        img_byte_arr = io.BytesIO()

        result.save(
            img_byte_arr,
            format="PNG"
        )

        return img_byte_arr.getvalue()

    except Exception as e:
        st.error(f"Gagal tambah teks: {e}")
        return main_image_bytes

# ==============================================================================
# UI STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Inamikro Ad Generator V8",
    layout="wide",
    page_icon="📈"
)

st.markdown(
    """
<style>
.main-header {
    text-align:center;
    padding:1rem;
}
.main-header h1 {
    color:#1565C0;
}
</style>
""",
    unsafe_allow_html=True
)

st.markdown(
    """
<div class="main-header">
<h1>📈 Inamikro Ad Generator</h1>
<p>Platform Konten Iklan UMKM Berbasis Agentic AI</p>
</div>
""",
    unsafe_allow_html=True
)

if not VERTEX_CONNECTION_SUCCESS:
    st.error(
        "⚠️ Vertex AI belum connect. "
        "Jalankan gcloud auth."
    )

# ==============================================================================
# SESSION STATE
# ==============================================================================
for k in [
    "main_text_result",
    "visual_prompt_result",
    "image_result_final",
    "model_used",
    "visual_prompt_version"
]:
    if k not in st.session_state:

        if k == "visual_prompt_version":
            st.session_state[k] = 0

        else:
            st.session_state[k] = None

# ==============================================================================
# LAYOUT
# ==============================================================================
col_form, col_result = st.columns(
    [1, 1.45],
    gap="large"
)

# ==============================================================================
# FORM INPUT
# ==============================================================================
with col_form:

    st.subheader("📋 Input UMKM")

    with st.container(border=True):

        logo_umkm = st.file_uploader(
            "Upload Logo",
            type=["png", "jpg", "jpeg"]
        )

        posisi_logo = st.selectbox(
            "Posisi Logo",
            [
                "Kanan Atas",
                "Kiri Atas",
                "Kanan Bawah",
                "Kiri Bawah"
            ]
        )

        nama_produk = st.text_input(
            "Nama Produk"
        )

        keywords_raw = st.text_input(
            "Keyword USP"
        )

        kategori = st.selectbox(
            "Kategori KBLI",
            KBLI_CATEGORIES
        )

        platform = st.radio(
            "Platform",
            [
                "Instagram",
                "WhatsApp",
                "TikTok"
            ]
        )

        mood_visual = st.selectbox(
            "Mood Visual",
            MOOD_OPTIONS
        )

        background = st.selectbox(
            "Background",
            list(BACKGROUND_OPTIONS.keys())
        )

        subjek = st.selectbox(
            "Subjek",
            SUBJEK_OPTIONS
        )

    btn_generate = st.button(
        "🚀 GENERATE IKLAN",
        type="primary",
        use_container_width=True
    )

# ==============================================================================
# RESULT
# ==============================================================================
with col_result:

    if btn_generate:

        with st.spinner(
            "🧠 Menjalankan Agentic AI..."
        ):

            llm = ChatVertexAI(
                model_name="gemini-2.5-pro"
            )

            prompt = f"""
{MASTER_PROMPT_FULL}

Produk: {nama_produk}
USP: {keywords_raw}
Platform: {platform}
Mood: {mood_visual}
Background: {background}
Subjek: {subjek}

WAJIB ADA:
**Ide Visual:**
"""

            raw_res = llm.invoke(
                [HumanMessage(content=prompt)]
            ).content

            vis_prompt, main_txt = parse_output_for_image(
                raw_res
            )

            st.session_state.main_text_result = main_txt
            st.session_state.visual_prompt_result = vis_prompt
            st.session_state.visual_prompt_version += 1

    # ==========================================================================
    # OUTPUT TEXT
    # ==========================================================================
    if st.session_state.main_text_result:

        st.markdown(
            st.session_state.main_text_result
        )

        st.divider()

        st.subheader("🎨 Komparasi Gambar")

        edited_visual_prompt = st.text_area(
            "Edit Prompt Visual",
            value=st.session_state.visual_prompt_result,
            height=100,
            key=f"vis_{st.session_state.visual_prompt_version}"
        )

        # Overlay text
        with st.expander(
            "✏️ Tambahkan Teks Brosur"
        ):

            preset_brosur = st.selectbox(
                "Preset",
                list(PRESET_BROSUR.keys())
            )

            teks_overlay = st.text_input(
                "Teks Brosur",
                value=PRESET_BROSUR.get(
                    preset_brosur,
                    ""
                )
            )

            col_t1, col_t2, col_t3 = st.columns(3)

            with col_t1:
                posisi_teks = st.selectbox(
                    "Posisi",
                    [
                        "Tengah Bawah",
                        "Tengah Atas",
                        "Kiri Atas",
                        "Kanan Bawah",
                        "Tengah"
                    ]
                )

            with col_t2:
                ukuran_font = st.slider(
                    "Ukuran Font",
                    24,
                    120,
                    64,
                    step=8
                )

            with col_t3:
                warna_teks = st.selectbox(
                    "Warna",
                    [
                        "⬜ Putih",
                        "🟡 Kuning",
                        "🟠 Oranye",
                        "⬛ Hitam",
                        "🔴 Merah"
                    ]
                )

            dengan_kotak = st.checkbox(
                "Tambahkan background kotak"
            )

        # Tabs
        t1, t2, t3 = st.tabs(
            [
                "🖼️ Imagen 3.0",
                "🎨 GPT Image 2",
                "⚡ Nano Banana 2"
            ]
        )

        # ----------------------------------------------------------------------
        # IMAGEN
        # ----------------------------------------------------------------------
        with t1:

            if st.button(
                "RENDER (IMAGEN)",
                use_container_width=True
            ):

                img = generate_imagen_image(
                    edited_visual_prompt
                )

                if img:

                    if logo_umkm:
                        img = apply_dynamic_branding(
                            img,
                            logo_umkm,
                            posisi_logo
                        )

                    if teks_overlay.strip():
                        img = add_text_overlay(
                            img,
                            teks_overlay,
                            posisi_teks,
                            ukuran_font,
                            warna_teks,
                            dengan_kotak
                        )

                    st.session_state.image_result_final = img
                    st.session_state.model_used = "Imagen 3.0"

        # ----------------------------------------------------------------------
        # GPT IMAGE 2
        # ----------------------------------------------------------------------
        with t2:

            if st.button(
                "RENDER (GPT IMAGE 2)",
                use_container_width=True
            ):

                img = generate_dalle_image(
                    edited_visual_prompt
                )

                if img:

                    if logo_umkm:
                        img = apply_dynamic_branding(
                            img,
                            logo_umkm,
                            posisi_logo
                        )

                    if teks_overlay.strip():
                        img = add_text_overlay(
                            img,
                            teks_overlay,
                            posisi_teks,
                            ukuran_font,
                            warna_teks,
                            dengan_kotak
                        )

                    st.session_state.image_result_final = img
                    st.session_state.model_used = "GPT Image 2"

        # ----------------------------------------------------------------------
        # GEMINI FLASH IMAGE
        # ----------------------------------------------------------------------
        with t3:

            if st.button(
                "RENDER (NANO BANANA 2)",
                use_container_width=True
            ):

                img = generate_gemini_flash_image(
                    edited_visual_prompt
                )

                if img:

                    if logo_umkm:
                        img = apply_dynamic_branding(
                            img,
                            logo_umkm,
                            posisi_logo
                        )

                    if teks_overlay.strip():
                        img = add_text_overlay(
                            img,
                            teks_overlay,
                            posisi_teks,
                            ukuran_font,
                            warna_teks,
                            dengan_kotak
                        )

                    st.session_state.image_result_final = img
                    st.session_state.model_used = "Nano Banana 2"

        # ==========================================================================
        # FINAL IMAGE
        # ==========================================================================
        if st.session_state.image_result_final:

            st.image(
                st.session_state.image_result_final,
                use_container_width=True,
                caption=f"✅ Dirender oleh: {st.session_state.model_used}"
            )