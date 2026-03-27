import os
import streamlit as st
import re

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
YOUR_PROJECT_ID = "careful-ensign-477104-p5"  # ID Projek Anda
YOUR_LOCATION = "us-central1"

VERTEX_CONNECTION_SUCCESS = False
try:
    if IS_VERTEX_AVAILABLE:
        vertexai.init(project=YOUR_PROJECT_ID, location=YOUR_LOCATION)
        VERTEX_CONNECTION_SUCCESS = True
except Exception as e:
    VERTEX_CONNECTION_SUCCESS = False
    print(f"Gagal init Vertex AI: {e}")

# --- DATA KATEGORI KBLI INAMIKRO ---
KBLI_CATEGORIES = [
    "56102 - Restoran dan Rumah Makan",
    "56303 - Rumah Minum/Kafe",
    "10794 - Industri Keripik & Makanan Ringan",
    "10750 - Industri Makanan Olahan (Frozen Food)",
    "47841 - Perdagangan Eceran Makanan Keliling",
    "47711 - Perdagangan Eceran Pakaian (Fashion)",
    "47726 - Perdagangan Eceran Sepatu/Sandal",
    "96012 - Jasa Penatu/Laundry",
    "96013 - Jasa Perawatan Sepatu/Tas",
    "85495 - Jasa Pendidikan/Bimbingan Belajar"
]

# ==============================================================================
# BAGIAN 2: FUNGSI ENGINE AI (FLASH & IMAGEN)
# ==============================================================================

def parse_output_for_image(markdown_text):
    """Mengekstrak 'Ide Visual' untuk diumpankan ke Imagen 3."""
    try:
        match = re.search(r"Ide Visual[\s:]*\*?(.*?)(?=\n\n|\Z)", markdown_text, re.IGNORECASE | re.DOTALL)
        if match:
            clean_idea = match.group(1).strip().replace('*', '').replace('\n', ' ')
            return clean_idea[:400]
    except Exception:
        pass
    return "" 

@st.cache_data(show_spinner=False)
def generate_imagen_image(prompt_text):
    """Menghasilkan gambar menggunakan Imagen 3."""
    if not IS_VERTEX_AVAILABLE or not VERTEX_CONNECTION_SUCCESS or not prompt_text:
        return None

    full_prompt = f"""
    professional product photography, {prompt_text},
    photorealistic, highly detailed, 8k resolution, commercial advertisement style,
    no text overlay, sharp focus, beautiful lighting.
    """
    try:
        # PERBAIKAN 1: Typo nama model. Yang benar pakai 'n' (imagen) bukan (image)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        response = model.generate_images(prompt=full_prompt, number_of_images=1, aspect_ratio="1:1")
        return response.images[0]._image_bytes
    except Exception as e:
        # PERBAIKAN 2: Jika masih gagal, kita panggil model versi sebelumnya (Imagen 2)
        try:
            model_fallback = ImageGenerationModel.from_pretrained("imagegeneration@006")
            response = model_fallback.generate_images(prompt=full_prompt, number_of_images=1)
            return response.images[0]._image_bytes
        except Exception as e_fallback:
            # PERBAIKAN 3: Memunculkan error asli di layar agar ketahuan penyebabnya
            st.error(f"Pesan Error Asli dari Google: {e_fallback}")
            return None

# MENGGUNAKAN MODEL FLASH & TOKEN BESAR (8192) AGAR TIDAK TERPOTONG
try:
    llm_flash = ChatVertexAI(
        model_name="gemini-2.5-flash",
        temperature=0.3, # Suhu diturunkan agar formatnya rapi & tidak basa-basi
        max_output_tokens=8192 
    )
except Exception:
    pass

@st.cache_data(show_spinner=False)
def generate_ad_text(kategori, user_input, gaya, platform):
    """Prompt Engineering Ketat untuk Teks Iklan."""
    
    base_prompt = f"""ANDA ADALAH SISTEM GENERATOR KONTEN IKLAN. 
DILARANG MEMBERIKAN AYAT PEMBUKA ATAU PENUTUP (SEPERTI "Tentu, ini kontennya").
LANGSUNG KELUARKAN HASIL BERDASARKAN FORMAT DI BAWAH INI.

PRODUK: {user_input} (Kategori: {kategori})
GAYA BAHASA: {gaya}
PLATFORM: {platform}
"""
    
    if "Instagram" in platform:
        base_prompt += """
FORMAT WAJIB:
## 📸 Headline: [Tulis Headline Catchy]
**Caption:**
[Tulis Caption Menarik 2-3 Paragraf dengan Emoji]

**Hashtags:**
[Tulis 5-8 Hashtags]

**Ide Visual:**
[Tulis SATU AYAT deskripsi SANGAT DETAIL DALAM BAHASA INGGRIS tentang foto produk ini tanpa ada teks di dalam gambarnya]
"""
    elif "WhatsApp" in platform:
        base_prompt += """
FORMAT WAJIB:
## 💬 Subject: [Tulis Subject Menarik]
**Isi Pesan:**
[Tulis Pesan Broadcast yang persuasif dan diakhiri Call-to-Action]

**Ide Visual:**
[Tulis SATU AYAT deskripsi SANGAT DETAIL DALAM BAHASA INGGRIS tentang foto produk untuk dilampirkan]
"""
    elif "TikTok" in platform:
        base_prompt += """
FORMAT WAJIB:
## 🎬 Judul Video: [Tulis Judul Video (Hook)]

**Scene 1 (Hook 0-3s):**
- **Visual Prompt (English):** [Deskripsi visual AI]
- **Voiceover (Indonesian):** [Skrip Audio]

**Scene 2 (Body 3-10s):**
- **Visual Prompt (English):** [Deskripsi visual AI]
- **Voiceover (Indonesian):** [Skrip Audio]

**Scene 3 (Call to Action 10-15s):**
- **Visual Prompt (English):** [Deskripsi visual AI]
- **Voiceover (Indonesian):** [Skrip Audio]

**Ide Visual:**
[Tulis SATU AYAT deskripsi SANGAT DETAIL DALAM BAHASA INGGRIS mengenai thumbnail video ini]
"""
    
    return llm_flash.invoke(base_prompt).content

# ==============================================================================
# BAGIAN 3: UI/UX STREAMLIT (SESUAI PROPOSAL SKRIPSI)
# ==============================================================================

st.set_page_config(page_title="Inamikro Ad Generator", layout="wide", page_icon="🛍️")

# --- HEADER APLIKASI ---
st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🚀 Inamikro Ad Generator</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Aplikasi Pembuat Konten Iklan UMKM Berbasis Generative AI (Gemini Flash & Imagen 3)</p>", unsafe_allow_html=True)
st.divider()

if not VERTEX_CONNECTION_SUCCESS:
    st.error("⚠️ Sistem Offline: Gagal terhubung ke Google Cloud Vertex AI (Cek Billing/Auth).")

# --- INISIALISASI STATE ---
if 'text_result' not in st.session_state: st.session_state.text_result = None
if 'image_result' not in st.session_state: st.session_state.image_result = None
if 'image_prompt' not in st.session_state: st.session_state.image_prompt = None

# --- LAYOUT UTAMA (2 KOLOM SESUAI PROPOSAL) ---
col_form, col_result = st.columns([1, 1.5], gap="large")

# ---------------------------------------------------------
# KOLOM KIRI: FORM INPUT PENGGUNA
# ---------------------------------------------------------
with col_form:
    st.markdown("### 📝 Langkah 1: Input Data Produk")
    with st.container(border=True):
        nama_produk = st.text_input("Nama Produk", placeholder="Contoh: Kopi Senja")
        deskripsi = st.text_area("Deskripsi Produk (USP)", placeholder="Contoh: Kopi susu aren murni, rasa creamy, harga 15rb.", height=100)
        kategori = st.selectbox("Kategori Usaha", KBLI_CATEGORIES)
        
    st.markdown("### 🎯 Langkah 2: Target Platform")
    with st.container(border=True):
        platform = st.radio("Pilih Kanal Distribusi", ["Instagram (Visual & Feed)", "WhatsApp (Broadcast Personal)", "TikTok (Video AI Script)"])
        gaya = st.selectbox("Gaya Bahasa", ["Santai & Kekinian", "Profesional & Elegan", "Promo Hard-Selling"])
        
    st.markdown("<br>", unsafe_allow_html=True)
    btn_generate_text = st.button("✨ GENERATE KONTEN IKLAN", type="primary", use_container_width=True, disabled=not VERTEX_CONNECTION_SUCCESS)

# ---------------------------------------------------------
# KOLOM KANAN: HASIL OUTPUT (TEKS & VISUAL)
# ---------------------------------------------------------
with col_result:
    st.markdown("### 📱 Langkah 3: Hasil Draft Konten")

    # 1. Eksekusi Generate Teks
    if btn_generate_text:
        if not nama_produk or not deskripsi:
            st.warning("⚠️ Sila isi Nama Produk dan Deskripsi terlebih dahulu.")
        else:
            st.session_state.image_result = None # Reset gambar lama
            with st.spinner("🤖 Menggunakan Gemini 2.5 Flash untuk menyusun narasi..."):
                text_res = generate_ad_text(kategori, f"{nama_produk}: {deskripsi}", gaya, platform)
                st.session_state.text_result = text_res
                st.session_state.image_prompt = parse_output_for_image(text_res)

    # 2. Tampilkan Hasil Teks
    if st.session_state.text_result:
        with st.container(border=True):
            st.markdown(st.session_state.text_result)
            
            st.divider()
            
            # 3. Tombol Generate Gambar (Hanya muncul jika teks sukses)
            if st.session_state.image_prompt:
                st.success("✅ Tag 'Ide Visual' berhasil dibuat. Siap untuk dirender.")
                btn_image = st.button("🎨 RENDER GAMBAR (Imagen 3)", type="primary", use_container_width=True)
                
                if btn_image:
                    with st.spinner("Memproses imej resolusi tinggi (Rasio 1:1)..."):
                        img_bytes = generate_imagen_image(st.session_state.image_prompt)
                        if img_bytes:
                            st.session_state.image_result = img_bytes
                        else:
                            st.error("⚠️ Gagal memproses gambar. Pastikan kuota Vertex AI tersedia.")
            else:
                 st.warning("⚠️ Gagal mendeteksi 'Ide Visual'. Silakan klik Generate Konten Iklan lagi.")

    # 4. Tampilkan Hasil Gambar
    if st.session_state.image_result:
        with st.container(border=True):
            st.markdown("#### 🖼️ Hasil Visual (AI Generated)")
            # Gambar ditengahkan dan dibatasi ukurannya agar UI rapi
            col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
            with col_img2:
                st.image(st.session_state.image_result, use_container_width=True)
                st.download_button(
                    label="⬇️ Download Visual", 
                    data=st.session_state.image_result, 
                    file_name="draft_iklan_inamikro.png", 
                    mime="image/png", 
                    use_container_width=True
                )

    # Placeholder saat kosong
    if not st.session_state.text_result:
        with st.container(border=True):
            st.info("👈 Silakan isi form di sebelah kiri untuk mulai menghasilkan draf iklan secara otomatis.")