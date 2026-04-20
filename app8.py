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

KBLI_CATEGORIES = [
    "56102 - Restoran dan Rumah Makan", "56303 - Rumah Minum/Kafe",
    "10794 - Industri Keripik & Makanan Ringan", "10750 - Industri Makanan Olahan (Frozen Food)",
    "47711 - Perdagangan Eceran Pakaian (Fashion)", "96012 - Jasa Penatu/Laundry",
    "85495 - Jasa Pendidikan/Bimbingan Belajar"
]

# ==============================================================================
# BAGIAN 2: ENGINE AI (AGENTIC PROMPTING & IMAGEN 3)
# ==============================================================================

def parse_output_for_image(markdown_text):
    """Memisahkan Ide Visual dari teks utama agar bisa diedit user."""
    try:
        match = re.search(r"\*\*Ide Visual:\*\*[\s]*(.*?)(?=\n\n|\Z)", markdown_text, re.IGNORECASE | re.DOTALL)
        if match:
            clean_idea = match.group(1).strip().replace('*', '').replace('\n', ' ')
            # Hapus bagian ide visual dari teks utama
            main_text = re.sub(r"\*\*Ide Visual:\*\*[\s]*(.*?)(?=\n\n|\Z)", "", markdown_text, flags=re.IGNORECASE | re.DOTALL)
            return clean_idea[:500], main_text.strip()
    except Exception:
        pass
    return "", markdown_text

@st.cache_data(show_spinner=False)
def generate_imagen_image(prompt_text):
    if not IS_VERTEX_AVAILABLE or not VERTEX_CONNECTION_SUCCESS or not prompt_text: return None
    full_prompt = f"professional product photography, {prompt_text}, photorealistic, highly detailed, 8k resolution, commercial advertisement style, no text overlay, sharp focus, beautiful lighting."
    try:
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        response = model.generate_images(prompt=full_prompt, number_of_images=1, aspect_ratio="1:1")
        return response.images[0]._image_bytes
    except Exception:
        return None

try:
    llm_pro = ChatVertexAI(model_name="gemini-2.5-pro", temperature=0.3, max_output_tokens=8192)
except Exception:
    pass

@st.cache_data(show_spinner=False)
def generate_ad_text_agentic(kategori, user_input, gaya, platform, market, mood, images_bytes_list):
    """Prompt Engineering dengan Role Agent sesuai masukan Pak Felix."""
    market_str = ", ".join(market)
    
    base_prompt = f"""ANDA ADALAH AGEN PAKAR MARKETING UNTUK KATEGORI: {kategori}.
TUGAS: Analisis input teks & gambar asli produk. Buat copywriting iklan yang TEPAT SASARAN.

PROFIL KAMPANYE (WAJIB DIPATUHI):
1. PRODUK & USP: {user_input}
2. TARGET MARKET: {market_str} (Gunakan bahasa yang relevan dengan mereka)
3. GAYA BAHASA: {gaya}
4. MOOD VISUAL: {mood} (Gunakan mood ini untuk menyusun Ide Visual)
5. PLATFORM: {platform}

ATURAN DUAL-FUSION: Replika komposisi latar gambar asli, tapi buat visual produknya terlihat premium sesuai mood {mood}.
"""
    
    if "Instagram" in platform:
        base_prompt += "\nFORMAT WAJIB:\n## 📸 Headline: [Headline]\n**Caption:**\n[Caption 2-3 Paragraf]\n**Hashtags:**\n[5-8 Hashtags]\n\n**Ide Visual:**\n[SATU AYAT BAHASA INGGRIS deskripsi visual produk yang mereplika foto asli tapi dengan mood " + mood + "]"
    elif "WhatsApp" in platform:
        base_prompt += "\nFORMAT WAJIB:\n## 💬 Subject: [Subject]\n**Isi Pesan:**\n[Pesan persuasif + Call to Action]\n\n**Ide Visual:**\n[SATU AYAT BAHASA INGGRIS deskripsi visual mood " + mood + "]"
    elif "TikTok" in platform:
        base_prompt += "\nFORMAT WAJIB:\n## 🎬 Judul Video: [Judul]\n**Scene 1 (0-3s):**\n- **Visual Prompt:** [AI Prompt]\n- **Voiceover:** [VO]\n**Scene 2 (3-10s):**\n- **Visual Prompt:** [AI Prompt]\n- **Voiceover:** [VO]\n\n**Ide Visual:**\n[SATU AYAT BAHASA INGGRIS deskripsi thumbnail video mood " + mood + "]"

    content_parts = [{"type": "text", "text": base_prompt}]
    for img_bytes in images_bytes_list:
        content_parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode('utf-8')}"}})
        
    return llm_pro.invoke([HumanMessage(content=content_parts)]).content

@st.cache_data(show_spinner=False)
def evaluate_ad_quality(user_input, target_market, generated_ad):
    """Fungsi AI Expert Reviewer (Fitur Penilai)."""
    eval_prompt = f"""ANDA ADALAH JURI PAKAR DIGITAL MARKETING INDONESIA.
Evaluasi iklan berikut apakah sudah sesuai dengan spesifikasi permintaan UMKM.

SPESIFIKASI UMKM:
- Produk & USP: {user_input}
- Target Market: {target_market}

HASIL IKLAN YANG DIEVALUASI:
{generated_ad}

Berikan ulasan singkat (Maksimal 3 kalimat) mengenai kekuatan dan kelemahan iklan ini.
Lalu, berikan SKOR KESESUAIAN (0-100%).
FORMAT WAJIB:
**Ulasan Pakar:** [Isi Ulasan]
**Skor Kualitas:** [Angka]/100
"""
    return llm_pro.invoke(eval_prompt).content

# ==============================================================================
# BAGIAN 3: MANIPULASI LOGO POSISI DINAMIS (PILLOW)
# ==============================================================================

def apply_dynamic_branding(main_image_bytes, logo_file_uploaded, posisi):
    if not main_image_bytes or not logo_file_uploaded: return main_image_bytes
    try:
        main_img = Image.open(io.BytesIO(main_image_bytes))
        main_w, main_h = main_img.size
        
        logo_img = Image.open(logo_file_uploaded)
        if logo_img.mode != 'RGBA': logo_img = logo_img.convert('RGBA')
            
        new_logo_w = int(main_w * 0.18)
        new_logo_h = int(new_logo_w * (logo_img.height / logo_img.width))
        logo_img = logo_img.resize((new_logo_w, new_logo_h), Image.Resampling.LANCZOS)
        
        alpha = logo_img.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(0.85)
        logo_img.putalpha(alpha)
        
        padding = 30
        if posisi == "Kanan Bawah": pos = (main_w - new_logo_w - padding, main_h - new_logo_h - padding)
        elif posisi == "Kiri Bawah": pos = (padding, main_h - new_logo_h - padding)
        elif posisi == "Kanan Atas": pos = (main_w - new_logo_w - padding, padding)
        elif posisi == "Kiri Atas": pos = (padding, padding)
        
        branded_img = main_img.copy()
        branded_img.paste(logo_img, pos, logo_img)
        
        img_byte_arr = io.BytesIO()
        branded_img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception:
        return main_image_bytes

# ==============================================================================
# BAGIAN 4: UI/UX STREAMLIT
# ==============================================================================

st.set_page_config(page_title="Inamikro Ad Generator V5", layout="wide", page_icon="📈")
st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🚀 Inamikro Ad Generator V5</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Agentic AI + Dynamic Logo + Expert Review (Sistem Evaluasi Otomatis)</p>", unsafe_allow_html=True)
st.divider()

if 'main_text_result' not in st.session_state: st.session_state.main_text_result = None
if 'visual_prompt_result' not in st.session_state: st.session_state.visual_prompt_result = None
if 'image_result_branded' not in st.session_state: st.session_state.image_result_branded = None
if 'ai_review_score' not in st.session_state: st.session_state.ai_review_score = None

col_form, col_result = st.columns([1, 1.4], gap="large")

with col_form:
    st.markdown("### 📋 1. Branding & Target")
    with st.container(border=True):
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            logo_umkm = st.file_uploader("Upload Logo", type=['png', 'jpg'])
        with col_l2:
            posisi_logo = st.selectbox("Posisi Logo", ["Kanan Bawah", "Kiri Bawah", "Kanan Atas", "Kiri Atas"])
        target_market = st.multiselect("Target Market", ["Mahasiswa", "Pekerja Kantoran", "Ibu Rumah Tangga", "Anak Sekolah", "Umum"], default=["Umum"])

    st.markdown("### 📝 2. Data Produk & Referensi")
    with st.container(border=True):
        nama_produk = st.text_input("Nama Produk", placeholder="Contoh: Kopi Senja")
        deskripsi = st.text_area("Deskripsi (USP)", placeholder="Contoh: Kopi aren murni, creamy...", height=80)
        kategori = st.selectbox("Kategori Usaha", KBLI_CATEGORIES)
        product_images = st.file_uploader("Upload Foto Referensi (Max 3)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    st.markdown("### 🎯 3. Strategi Marketing")
    with st.container(border=True):
        platform = st.radio("Platform", ["Instagram (Visual & Feed)", "WhatsApp (Broadcast)", "TikTok (Video AI Script)"])
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            gaya = st.selectbox("Tone of Voice", ["Santai & Kekinian", "Profesional & Elegan", "Promo Hard-Selling"])
        with col_s2:
            mood_visual = st.selectbox("Mood Visual", ["Cerah & Ceria", "Gelap & Elegan", "Minimalis", "Hangat & Estetik"])
        
    st.markdown("<br>", unsafe_allow_html=True)
    btn_generate = st.button("🚀 GENERATE IKLAN", type="primary", use_container_width=True, disabled=not VERTEX_CONNECTION_SUCCESS)

with col_result:
    st.markdown("### 📱 4. Hasil Produksi AI")

    if btn_generate:
        if not nama_produk or not deskripsi:
            st.warning("⚠️ Isi Nama Produk dan Deskripsi.")
        else:
            st.session_state.image_result_branded = None
            st.session_state.ai_review_score = None
            with st.spinner("🧠 Agent AI sedang menganalisis spesifikasi & target market..."):
                images_data = [img.getvalue() for img in product_images] if product_images else []
                raw_res = generate_ad_text_agentic(kategori, f"{nama_produk}: {deskripsi}", gaya, platform, target_market, mood_visual, images_data)
                
                vis_prompt, main_txt = parse_output_for_image(raw_res)
                st.session_state.main_text_result = main_txt
                st.session_state.visual_prompt_result = vis_prompt

    if st.session_state.main_text_result:
        with st.container(border=True):
            st.markdown(st.session_state.main_text_result)
            
            # --- FITUR AI REVIEWER (Jawaban untuk Pak Felix) ---
            if st.button("🤖 Minta Penilaian Pakar (AI Evaluator)"):
                with st.spinner("AI sedang mengevaluasi kualitas iklan..."):
                    st.session_state.ai_review_score = evaluate_ad_quality(f"{nama_produk}: {deskripsi}", ", ".join(target_market), st.session_state.main_text_result)
            
            if st.session_state.ai_review_score:
                st.info(st.session_state.ai_review_score)
            
            st.divider()
            
            # --- FITUR EDIT VISUAL PROMPT (Jawaban untuk Pak Greg) ---
            st.markdown("#### 🎨 Tahap Pra-Render Gambar")
            st.caption("AI telah merumuskan prompt visual (bahasa Inggris) di bawah ini. Anda bisa mengeditnya sebelum gambar diproses.")
            
            edited_visual_prompt = st.text_area("Instruksi ke AI Gambar (Editable):", value=st.session_state.visual_prompt_result, height=80)
            
            if edited_visual_prompt:
                if st.button("✨ RENDER GAMBAR SEKARANG (Imagen 3)", type="primary", use_container_width=True):
                    with st.spinner("Memproses imej resolusi tinggi..."):
                        img_raw_bytes = generate_imagen_image(edited_visual_prompt)
                        if img_raw_bytes and logo_umkm:
                            with st.spinner(f"Menempelkan Logo di {posisi_logo}..."):
                                st.session_state.image_result_branded = apply_dynamic_branding(img_raw_bytes, logo_umkm, posisi_logo)
                        else:
                            st.session_state.image_result_branded = img_raw_bytes
                        st.balloons()

    if st.session_state.image_result_branded:
        with st.container(border=True):
            col_img1, col_img2, col_img3 = st.columns([1, 3, 1])
            with col_img2:
                st.image(st.session_state.image_result_branded, use_container_width=True)
                st.download_button("⬇️ Download Visual Final", st.session_state.image_result_branded, "iklan_inamikro.png", "image/png", use_container_width=True)

    if not st.session_state.main_text_result:
        with st.container(border=True):
            st.info("👈 Silakan isi spesifikasi di panel kiri, lalu klik 'GENERATE IKLAN'.")