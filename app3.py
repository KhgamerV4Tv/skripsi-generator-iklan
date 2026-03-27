import os
import pandas as pd
import streamlit as st
import re
import time 

# Import LangChain & Vertex AI
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import SentenceTransformerEmbeddings

try:
    import vertexai
    from langchain_google_vertexai import ChatVertexAI
    from vertexai.vision_models import ImageGenerationModel
    IS_VERTEX_AVAILABLE = True
except ImportError:
    IS_VERTEX_AVAILABLE = False
    print("Peringatan: Library Vertex AI belum terinstal.")

# ==============================================================================
# BAGIAN 2: SETUP PROJECT & HELPER
# ==============================================================================

# --- KONFIGURASI GCP ---
YOUR_PROJECT_ID = "careful-ensign-477104-p5"  # Ganti dengan ID Project
YOUR_LOCATION = "us-central1"

# --- INIT VERTEX AI ---
VERTEX_CONNECTION_SUCCESS = False
try:
    if IS_VERTEX_AVAILABLE:
        vertexai.init(project=YOUR_PROJECT_ID, location=YOUR_LOCATION)
        VERTEX_CONNECTION_SUCCESS = True
    else:
        VERTEX_CONNECTION_SUCCESS = False
except Exception as e:
    VERTEX_CONNECTION_SUCCESS = False
    print(f"Gagal init Vertex AI: {e}")

# --- KBLI DATA ---
KBLI_CATEGORIES = {
    "56102 - Restoran dan Rumah Makan": "Restoran, contoh: Ayam Geprek, Warteg",
    "56303 - Rumah Minum/Kafe": "Kafe atau kedai minuman, contoh: Kopi Susu, Boba",
    "10794 - Industri Keripik": "Industri makanan ringan, contoh: Keripik, Basreng",
    "47711 - Perdagangan Eceran Pakaian": "Toko baju, contoh: Gamis, Kemeja",
    "47726 - Perdagangan Eceran Sepatu": "Toko sepatu, contoh: Sneakers, Sandal",
    "96012 - Jasa Penatu/Laundry Kiloan": "Jasa laundry pakaian kiloan",
    "96013 - Jasa Perawatan Sepatu/Tas": "Jasa cuci atau reparasi sepatu dan tas",
    "47841 - Perdagangan Eceran Makanan Keliling": "Makanan keliling, contoh: Martabak, Roti Bakar",
    "10750 - Industri Makanan Olahan": "Makanan olahan, contoh: Frozen Food, Sambal",
    "85495 - Pendidikan Bimbingan Belajar": "Jasa bimbingan belajar atau les privat"
}

def parse_output_for_image(markdown_text):
    """Mencari teks setelah 'Ide Visual:' untuk dijadikan prompt gambar Imagen 3."""
    try:
        match = re.search(r"Ide Visual:[\s\*]*(.*?)(?=\n-|\n\n|$)", markdown_text, re.IGNORECASE | re.DOTALL)
        if match:
            clean_idea = match.group(1).strip().replace('*', '').replace('\n', ' ')
            return clean_idea[:400]
    except Exception:
        pass
    return "" 

# --- FUNGSI GENERATE GAMBAR (IMAGEN 3) ---
@st.cache_data(show_spinner=False)
def generate_imagen_image(prompt_text):
    if not IS_VERTEX_AVAILABLE or not VERTEX_CONNECTION_SUCCESS or not prompt_text:
        return None

    # Prompt engineering khusus untuk Imagen agar hasilnya fotorealistik
    full_prompt = f"""
    professional product photography, {prompt_text},
    photorealistic, cinematic lighting, 8k resolution, commercial advertisement style,
    no text overlay, sharp focus.
    """
    
    try:
        model = ImageGenerationModel.from_pretrained("image-3.0-generate-001")
        response = model.generate_images(prompt=full_prompt, number_of_images=1, aspect_ratio="1:1")
        return response.images[0]._image_bytes
    except Exception as e:
        try:
             model = ImageGenerationModel.from_pretrained("imagegeneration@006")
             response = model.generate_images(prompt=full_prompt, number_of_images=1)
             return response.images[0]._image_bytes
        except Exception:
            return None

# ==============================================================================
# BAGIAN 3: FUNGSI LLM UTAMA (DYNAMIC PROMPTING)
# ==============================================================================

try:
    llm_pro = ChatVertexAI(
        model_name="gemini-2.5-pro",
        temperature=0.7,
        max_output_tokens=1024
    )
except:
    llm_pro = ChatVertexAI(model_name="gemini-2.5-pro", temperature=0.7)

@st.cache_data(show_spinner=False)
def generate_ad_text(kategori, user_input, gaya, platform):
    """Menghasilkan teks iklan dengan struktur prompt yang disesuaikan per platform."""
    
    base_prompt = f"""
    Anda adalah Copywriter dan Digital Marketer Senior.
    TUGAS: Buat konten iklan promosi untuk platform {platform}.
    PRODUK: {user_input} (Kategori: {kategori}).
    GAYA BAHASA: {gaya}.
    """
    
    if "Instagram" in platform:
        base_prompt += """
        OUTPUT FORMAT (Markdown):
        ## 📸 Headline: [Pendek & Catchy]
        **Caption:**
        [Storytelling menarik, gunakan emoji yang relevan]
        **Hashtags:**
        [5-10 hashtag]
        
        **Ide Visual:**
        [Berikan 1 kalimat deskripsi SANGAT DETAIL DALAM BAHASA INGGRIS tentang foto produk ini. Contoh: "A cup of coffee on a wooden table with coffee beans scattered around, cinematic lighting"]
        """
    elif "WhatsApp" in platform:
        base_prompt += """
        OUTPUT FORMAT (Markdown):
        ## 💬 Subject: [Judul Pesan Menarik]
        **Isi Pesan:**
        [Sapaan personal, to the point, cantumkan penawaran/keunggulan, akhiri dengan Call-to-Action]
        
        **Ide Visual:**
        [Berikan 1 kalimat deskripsi DETAIL DALAM BAHASA INGGRIS tentang foto produk yang cocok dilampirkan di WhatsApp]
        """
    elif "TikTok" in platform:
        base_prompt += """
        TUGAS KHUSUS TIKTOK: Naskah ini HARUS kompatibel untuk diinput ke AI Video Generator (seperti Luma Dream Machine atau Runway Gen-2).
        
        OUTPUT FORMAT (Markdown):
        ## 🎬 Judul Video: [Judul Catchy]
        
        **Scene 1 (Hook - 0-3s):**
        - **Visual Prompt (English):** [Deskripsi visual SANGAT DETAIL dalam bahasa Inggris untuk AI Video. Contoh: "Cinematic close up of a steaming cup of coffee, slow zoom in"]
        - **Voiceover (Indonesian):** [Teks narasi]
        
        **Scene 2 (Body - 3-10s):**
        - **Visual Prompt (English):** [Deskripsi visual detail]
        - **Voiceover (Indonesian):** [Teks narasi]
        
        **Scene 3 (CTA - 10-15s):**
        - **Visual Prompt (English):** [Deskripsi visual detail]
        - **Voiceover (Indonesian):** [Teks narasi]

        **Ide Visual:**
        [Berikan 1 kalimat deskripsi DALAM BAHASA INGGRIS mengenai thumbnail/cover video ini untuk digenerate oleh AI gambar]
        """
    
    return llm_pro.invoke(base_prompt).content

# ==============================================================================
# BAGIAN 4: UI STREAMLIT
# ==============================================================================

st.set_page_config(page_title="Inamikro AI Generator", layout="wide")
st.title("🚀 Inamikro Ad Generator")
st.markdown("Solusi cerdas pembuatan konten iklan UMKM multi-platform berbasis Generative AI.")

if not VERTEX_CONNECTION_SUCCESS:
    st.error("⚠️ System Offline: Gagal terhubung ke Google Cloud Vertex AI. Pastikan kredensial (gcloud auth) sudah aktif.", icon="🔴")

if 'text_result' not in st.session_state: st.session_state.text_result = None
if 'image_result' not in st.session_state: st.session_state.image_result = None
if 'image_prompt' not in st.session_state: st.session_state.image_prompt = None

# --- LAYOUT DUA KOLOM ---
col_input, col_output = st.columns([1, 1.5], gap="large")

with col_input:
    with st.container(border=True):
        st.subheader("🛠️ 1. Input Data Usaha")
        nama_produk = st.text_input("Nama Produk/Brand", placeholder="Contoh: Kopi Kenangan Mantan")
        kategori = st.selectbox("Kategori KBLI Inamikro", list(KBLI_CATEGORIES.keys()))
        deskripsi = st.text_area("Deskripsi & Keunggulan", placeholder="Contoh: Kopi susu gula aren murni, rasa creamy, harga Rp 15.000.", height=100)
        
        st.subheader("🎯 2. Strategi Distribusi")
        platform = st.selectbox("Pilih Platform", ["Instagram (Visual Feed)", "WhatsApp (Broadcast)", "TikTok (AI Video Script)"])
        gaya = st.selectbox("Gaya Bahasa (Tone of Voice)", ["Santai & Gaul", "Profesional & Elegan", "Promo Hard-Selling"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        btn_text = st.button("✨ GENERATE KONTEN", type="primary", use_container_width=True, disabled=not VERTEX_CONNECTION_SUCCESS)

with col_output:
    st.subheader("📱 3. Hasil Produksi AI")

    # --- PROSES GENERATE ---
    if btn_text:
        if not nama_produk or not deskripsi:
            st.warning("Mohon lengkapi Nama Produk dan Deskripsi.")
        else:
            st.session_state.image_result = None 
            with st.spinner("Meracik strategi konten dan *copywriting*..."):
                text_res = generate_ad_text(kategori, f"{nama_produk}: {deskripsi}", gaya, platform)
                st.session_state.text_result = text_res
                st.session_state.image_prompt = parse_output_for_image(text_res)

    # --- TAMPILAN TEKS ---
    if st.session_state.text_result:
        with st.container(border=True):
            st.markdown(st.session_state.text_result)
            
            st.divider()
            st.info("💡 Klik tombol di bawah untuk mengeksekusi 'Ide Visual' menjadi gambar fotorealistik.")

            # --- TOMBOL GENERATE GAMBAR ---
            if st.session_state.image_prompt:
                btn_image = st.button("🎨 GENERATE VISUAL (Imagen 3)", type="secondary", use_container_width=True)
                
                if btn_image:
                    with st.spinner("Sedang memproses text-to-image synthesis (Rasio 1:1)..."):
                        img_bytes = generate_imagen_image(st.session_state.image_prompt)
                        if img_bytes:
                            st.session_state.image_result = img_bytes
                        else:
                            st.error("Gagal memproses gambar. Pastikan kuota Vertex AI Vision tersedia.")
            else:
                 st.warning("Sistem tidak mendeteksi parameter 'Ide Visual' untuk dirender.")

    # --- TAMPILAN GAMBAR ---
    if st.session_state.image_result:
        with st.container(border=True):
            # Membatasi lebar gambar agar UI tetap proporsional
            st.image(st.session_state.image_result, caption=f"Visual Generated by Imagen 3 for {nama_produk}", width=400)
            
            st.download_button(
                label="⬇️ Download Aset Visual", 
                data=st.session_state.image_result, 
                file_name="aset_iklan_inamikro.png", 
                mime="image/png", 
                use_container_width=True
            )

    if not st.session_state.text_result:
        st.info("👈 Lengkapi data di panel kiri, lalu klik 'GENERATE KONTEN' untuk memulai proses.")