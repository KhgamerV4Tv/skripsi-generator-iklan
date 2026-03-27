import os
import streamlit as st
import re
import io
import base64
from PIL import Image
from langchain_core.messages import HumanMessage

# Import Vertex AI & LangChain
try:
    import vertexai
    from langchain_google_vertexai import ChatVertexAI
    from vertexai.vision_models import ImageGenerationModel
    IS_VERTEX_AVAILABLE = True
except ImportError:
    IS_VERTEX_AVAILABLE = False
    st.error("⚠️ Peringatan: Library Vertex AI belum dipasang.")

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
    "47841 - Perdagangan Eceran Makanan Keliling", "47711 - Perdagangan Eceran Pakaian (Fashion)",
    "47726 - Perdagangan Eceran Sepatu/Sandal", "96012 - Jasa Penatu/Laundry",
    "96013 - Jasa Perawatan Sepatu/Tas", "85495 - Jasa Pendidikan/Bimbingan Belajar"
]

# ==============================================================================
# BAGIAN 2: ENGINE AI (MULTIMODAL BASE64 & IMAGEN)
# ==============================================================================

def parse_output_for_image(markdown_text):
    try:
        match = re.search(r"Ide Visual[\s:]*\*?(.*?)(?=\n\n|\Z)", markdown_text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip().replace('*', '').replace('\n', ' ')[:400]
    except: pass
    return "" 

@st.cache_data(show_spinner=False)
def generate_imagen_image(prompt_text):
    if not IS_VERTEX_AVAILABLE or not VERTEX_CONNECTION_SUCCESS or not prompt_text: return None
    full_prompt = f"professional product photography, {prompt_text}, photorealistic, 8k resolution, commercial advertisement style, no text overlay, sharp focus."
    try:
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        response = model.generate_images(prompt=full_prompt, number_of_images=1, aspect_ratio="1:1")
        return response.images[0]._image_bytes
    except: return None

# UPGRADE 1: UBAH KE GEMINI 2.5 PRO BIAR JAUH LEBIH PINTAR BACA GAMBAR
try:
    llm_pro = ChatVertexAI(model_name="gemini-2.5-pro", temperature=0.3, max_output_tokens=8192)
except: pass

@st.cache_data(show_spinner=False)
def generate_ad_text_multimodal(kategori, user_input, gaya, platform, images_bytes_list, instruksi_revisi=""):
    content_parts = []
    
    # UPGRADE 2: PROMPT DI-HACK SUPAYA PINTAR MENANGANI GAMBAR KOLASE
    system_text = f"""ANDA ADALAH SISTEM COPYWRITER MULTIMODAL KELAS ATAS. 
TUGAS: Buat konten iklan berdasarkan teks deskripsi DAN gambar asli yang dilampirkan.

ATURAN 'IDE VISUAL' (SANGAT PENTING):
- Jika foto asli berupa kolase atau banyak objek, IDENTIFIKASI produk utamanya saja berdasarkan deskripsi pengguna.
- BIKIN PINTAR: Jangan meniru keberantakan/teks pada foto asli. Buat instruksi visual yang SANGAT SPESIFIK, MEWAH, dan MENGGUGAH SELERA. 
- Contoh: Jika pengguna menyebut "keju creamy", instruksikan visualnya agar terlihat ada keju yang lumer. Integrasikan elemen teks pengguna ke dalam visual.

DATA PRODUK: {user_input} (Kategori: {kategori})
GAYA BAHASA: {gaya} | PLATFORM: {platform}
"""
    
    if instruksi_revisi:
        system_text += f"\n\n🚨 INSTRUKSI REVISI DARI USER: {instruksi_revisi}\nTolong ubah draf sebelumnya sesuai permintaan revisi ini!\n"
    
    if "Instagram" in platform:
        system_text += "\nFORMAT WAJIB:\n## 📸 Headline: [Headline]\n**Caption:**\n[Caption]\n**Hashtags:**\n[Hashtags]\n**Ide Visual:**\n[SATU AYAT deskripsi SANGAT DETAIL DALAM BAHASA INGGRIS mereplika produk asli tapi dalam nuansa studio iklan profesional]\n"
    elif "WhatsApp" in platform:
        system_text += "\nFORMAT WAJIB:\n## 💬 Subject: [Subject]\n**Isi Pesan:**\n[Isi]\n**Ide Visual:**\n[SATU AYAT deskripsi SANGAT DETAIL DALAM BAHASA INGGRIS mereplika produk asli dalam nuansa elegan]\n"
    elif "TikTok" in platform:
        system_text += "\nFORMAT WAJIB:\n## 🎬 Judul Video: [Judul]\n**Scene 1 (0-3s):**\n- **Visual Prompt (English):** [AI Prompt]\n- **Voiceover:** [VO]\n**Scene 2 (3-10s):**\n- **Visual Prompt (English):** [AI Prompt]\n- **Voiceover:** [VO]\n**Ide Visual:**\n[SATU AYAT deskripsi SANGAT DETAIL DALAM BAHASA INGGRIS untuk cover video yang estetis]\n"

    content_parts.append({"type": "text", "text": system_text})
    
    # Encoding Base64
    for img_bytes in images_bytes_list:
        base64_image = base64.b64encode(img_bytes).decode('utf-8')
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
        
    message = HumanMessage(content=content_parts)
    # Panggil llm_pro, bukan llm_flash
    return llm_pro.invoke([message]).content

# ==============================================================================
# BAGIAN 3: MANIPULASI LOGO (PILLOW)
# ==============================================================================
def apply_logo_watermark(main_image_bytes, logo_file_uploaded):
    if not main_image_bytes or not logo_file_uploaded: return main_image_bytes
    try:
        main_img = Image.open(io.BytesIO(main_image_bytes))
        main_w, main_h = main_img.size
        logo_img = Image.open(logo_file_uploaded)
        if logo_img.mode != 'RGBA': logo_img = logo_img.convert('RGBA')
        logo_aspect_ratio = logo_img.height / logo_img.width
        new_logo_w = int(main_w * 0.15)
        new_logo_h = int(new_logo_w * logo_aspect_ratio)
        logo_img = logo_img.resize((new_logo_w, new_logo_h), Image.Resampling.LANCZOS)
        watermarked_img = main_img.copy()
        watermarked_img.paste(logo_img, (main_w - new_logo_w - 20, main_h - new_logo_h - 20), logo_img)
        img_byte_arr = io.BytesIO()
        watermarked_img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except: return main_image_bytes

# ==============================================================================
# BAGIAN 4: UI STREAMLIT
# ==============================================================================

st.set_page_config(page_title="Inamikro Ad Generator PRO", layout="wide")

st.markdown("<h1 style='text-align: center; color: #1E88E5;'>📈 Inamikro Ad Generator PRO</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Multimodal Input + Logo Watermarking + Chatbot Revisi Otomatis</p>", unsafe_allow_html=True)
st.divider()

if 'text_result' not in st.session_state: st.session_state.text_result = None
if 'image_result_watermarked' not in st.session_state: st.session_state.image_result_watermarked = None
if 'image_prompt' not in st.session_state: st.session_state.image_prompt = None

col_form, col_result = st.columns([1, 1.4], gap="large")

with col_form:
    st.markdown("### 📋 Langkah 1: Branding")
    logo_umkm = st.file_uploader("Upload Logo UMKM (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
        
    st.markdown("### 📝 Langkah 2: Data & Visual")
    nama_produk = st.text_input("Nama Produk", "Bakwan Sowan")
    deskripsi = st.text_area("Deskripsi (USP)", "Rasa enak, keju creamy, banyak varian siomay nori.")
    kategori = st.selectbox("Kategori Usaha", KBLI_CATEGORIES, index=3)
    product_images = st.file_uploader("Upload Foto Asli (Max 3)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        
    st.markdown("### 🎯 Langkah 3: Distribusi")
    platform = st.radio("Kanal", ["Instagram (Visual & Feed)", "WhatsApp (Broadcast)", "TikTok (AI Video Script)"])
    gaya = st.selectbox("Gaya Bahasa", ["Santai & Kekinian", "Profesional & Elegan", "Promo Hard-Selling"])
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 GENERATE DRAFT", type="primary", use_container_width=True):
        st.session_state.image_result_watermarked = None
        with st.spinner("🧠 Menganalisis Teks & Piksel Gambar..."):
            images_data = [img.getvalue() for img in product_images] if product_images else []
            text_res = generate_ad_text_multimodal(kategori, f"{nama_produk}: {deskripsi}", gaya, platform, images_data)
            st.session_state.text_result = text_res
            st.session_state.image_prompt = parse_output_for_image(text_res)

with col_result:
    st.markdown("### 📱 Langkah 4: Hasil Produksi")

    if st.session_state.text_result:
        with st.container(border=True):
            st.markdown(st.session_state.text_result)
            st.divider()
            
            if st.session_state.image_prompt:
                if st.button("🎨 RENDER VISUAL + LOGO", type="primary", use_container_width=True):
                    with st.spinner("Memproses gambar resolusi tinggi..."):
                        img_raw = generate_imagen_image(st.session_state.image_prompt)
                        st.session_state.image_result_watermarked = apply_logo_watermark(img_raw, logo_umkm) if img_raw else None

    if st.session_state.image_result_watermarked:
        with st.container(border=True):
            col_img1, col_img2, col_img3 = st.columns([1, 3, 1])
            with col_img2:
                st.image(st.session_state.image_result_watermarked, use_container_width=True)
                st.download_button("⬇️ Download Final", st.session_state.image_result_watermarked, "iklan.png", "image/png", use_container_width=True)

    # ==============================================================================
    # LANGKAH 5: CHATBOT REVISI (FITUR BARU)
    # ==============================================================================
    if st.session_state.text_result:
        st.markdown("### 🤖 Langkah 5: Asisten Revisi Cepat")
        st.info("Kurang puas dengan hasilnya? Ketik permintaan revisi di bawah (misal: 'Ubah gambar jadi warna gelap' atau 'Ganti gaya bahasanya jadi lebih formal').")
        
        revisi_input = st.chat_input("Ketik instruksi revisi di sini...")
        if revisi_input:
            st.session_state.image_result_watermarked = None # Reset gambar lama
            with st.spinner("Memproses revisi sesuai permintaan Anda..."):
                images_data = [img.getvalue() for img in product_images] if product_images else []
                # Panggil AI lagi, tapi kali ini sertakan instruksi revisi
                new_text_res = generate_ad_text_multimodal(kategori, f"{nama_produk}: {deskripsi}", gaya, platform, images_data, instruksi_revisi=revisi_input)
                
                st.session_state.text_result = new_text_res
                st.session_state.image_prompt = parse_output_for_image(new_text_res)
                st.rerun() # Refresh tampilan otomatis