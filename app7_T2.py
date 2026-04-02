import os
import streamlit as st
import re
import io
import base64
from PIL import Image, ImageEnhance # Library Pillow untuk manipulasi gambar

# Import Vertex AI & LangChain
try:
    import vertexai
    from langchain_google_vertexai import ChatVertexAI
    from vertexai.vision_models import ImageGenerationModel
    from langchain_core.messages import HumanMessage
    IS_VERTEX_AVAILABLE = True
except ImportError:
    IS_VERTEX_AVAILABLE = False
    st.error("⚠️ Peringatan: Library Vertex AI atau LangChain belum dipasang di environment.")

# ==============================================================================
# BAGIAN 1: KONFIGURASI VERTEX AI (GCP)
# ==============================================================================
# Sesuai Screenshot image_8.png, project sudah terhubung billing.
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
# BAGIAN 2: FUNGSI ENGINE AI (GEMINI PRO MULTIMODAL & IMAGEN 3)
# ==============================================================================

def parse_output_for_image(markdown_text):
    """Mengekstrak 'Ide Visual' untuk diumpankan ke Imagen 3."""
    try:
        # Peningkatan regex untuk menangkap Ide Visual lebih akurat
        match = re.search(r"Ide Visual[\s:]*\*?(.*?)(?=\n\n|\Z)", markdown_text, re.IGNORECASE | re.DOTALL)
        if match:
            clean_idea = match.group(1).strip().replace('*', '').replace('\n', ' ')
            return clean_idea[:500]
    except Exception:
        pass
    return "" 

@st.cache_data(show_spinner=False)
def generate_imagen_image(prompt_text):
    """Menghasilkan gambar menggunakan Imagen 3."""
    if not IS_VERTEX_AVAILABLE or not VERTEX_CONNECTION_SUCCESS or not prompt_text:
        return None

    # Prompt internal paksaan agar Imagen fokus membuat visual iklan profesional
    full_prompt = f"""
    professional product photography, {prompt_text},
    photorealistic, highly detailed, 8k resolution, commercial advertisement style,
    no text overlay, sharp focus, beautiful lighting.
    """
    
    try:
        # Menggunakan Imagen 3.0 terbaru sesuai target skripsi
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        response = model.generate_images(prompt=full_prompt, number_of_images=1, aspect_ratio="1:1")
        return response.images[0]._image_bytes
    except Exception as e:
        # st.error(f"Imagen Error: {e}")
        return None

# MENGGUNAKAN GEMINI 2.5 PRO (Sesuai kesepakatan agar lebih pintar baca gambar kolase)
try:
    llm_pro = ChatVertexAI(
        model_name="gemini-2.5-pro",
        temperature=0.3, # Suhu diturunkan agar formatnya rapi & anti basa-basi
        max_output_tokens=8192 
    )
except Exception:
    pass

@st.cache_data(show_spinner=False)
def generate_ad_text_multimodal(kategori, user_input, gaya, platform, images_bytes_list, instruksi_revisi=""):
    """Prompt Engineering Ketat untuk Teks Iklan, mendukung Multimodal & Revisi."""
    
    base_prompt = f"""ANDA ADALAH SISTEM GENERATOR KONTEN IKLAN CERDAS MULTIMODAL. 
TUGAS: Analisis input teks DAN piksel gambar-gambar asli produk (kolase) yang dilampirkan pengguna. Buat copywriting iklan yang SANGAT RELEVAN.

ATURAN VISUAL PINTAR (Wajib Dituruti):
- Jika foto asli berupa kolase (banyak objek), IDENTIFIKASI produk utama berdasarkan deskripsi pengguna (misal: Bakwan).
- JANGAN mereplika keberantakan atau teks poster yang salah letak pada foto asli. Buat instruksi visual profesional yang bersih.
- DUAL-FUSION: Anda HARUS mereplika tata letak/komposisi dasar (misal meja kayu/koper) dari foto asli, tapi memanipulasi objek produk agar keju terlihat meleleh creamy lumer atau siomay nori terlihat gurih di draf visual profesional.

DATA PRODUK: {user_input} (Kategori: {kategori})
GAYA BAHASA: {gaya} | PLATFORM: {platform}
"""
    
    if instruksi_revisi:
        system_text_revisi = f"\n\n🚨 INSTRUKSI REVISI DARI USER (Prioritaskan Ini): {instruksi_revisi}\nTolong ubah draf sebelumnya sesuai permintaan revisi ini!\n"
        base_prompt += system_text_revisi
    
    if "Instagram" in platform:
        base_prompt += """
FORMAT WAJIB:
## 📸 Headline: [Tulis Headline Catchy]
**Caption:**
[Tulis Caption Menarik 2-3 Paragraf dengan Emoji]

**Hashtags:**
[Tulis 5-8 Hashtags]

**Ide Visual:**
[Tulis SATU AYAT deskripsi SANGAT DETAIL DALAM BAHASA INGGRIS mereplika produk asli dalam tata letak foto asli (meja kayu/koper) tapi suasana iklan profesional tanpa teks di gambar, pastikan detail visual Dual-Fusion lumer/gurih terlihat jelas]
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
    
    # Membuat Pesan Multimodal (Teks + Gambar Base64)
    content_parts = [{"type": "text", "text": base_prompt}]
    
    for img_bytes in images_bytes_list:
        base64_image = base64.b64encode(img_bytes).decode('utf-8')
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
        
    message = HumanMessage(content=content_parts)
    return llm_pro.invoke([message]).content

# ==============================================================================
# BAGIAN 3: ADVANCED LOGO BLENDING (PILLOW) - PERBAIKAN POSISI POJOK
# ==============================================================================

def apply_advanced_branding(main_image_bytes, logo_file_uploaded):
    """
    Logika manipulasi gambar pintar untuk mengintegrasikan logo.
    PERBAIKAN: Memindahkan logo ke pojok kanan bawah agar tidak menutupi produk utama.
    """
    if not main_image_bytes or not logo_file_uploaded:
        return main_image_bytes
        
    try:
        # 1. Buka Gambar Utama (AI Result)
        main_img = Image.open(io.BytesIO(main_image_bytes))
        main_w, main_h = main_img.size
        
        # 2. Buka Logo UMKM dan pastikan RGBA (transparansi)
        logo_img = Image.open(logo_file_uploaded)
        if logo_img.mode != 'RGBA':
            logo_img = logo_img.convert('RGBA')
            
        # 3. Resize Logo (Cukup kecil agar tidak mengganggu, misal 18% dari lebar gambar)
        new_logo_w = int(main_w * 0.18)
        logo_aspect_ratio = logo_img.height / logo_img.width
        new_logo_h = int(new_logo_w * logo_aspect_ratio)
        logo_img = logo_img.resize((new_logo_w, new_logo_h), Image.Resampling.LANCZOS)
        
        # --- PERBAIKAN INTEGRASI: MENEMPEL DI POJOK KANAN BAWAH (Seperti image_9.png) ---
        # Padding agar tidak menempel pas di pinggir (misal 30px)
        padding = 30
        position_x = main_w - new_logo_w - padding
        position_y = main_h - new_logo_h - padding
        
        # --- INTEGRASI PINTAR: MENAMBAHKAN OPACITY (TRANSPARANSI) ---
        # Kunci agar logo terlihat tercetak, bukan ditempel. Kita buat logo 85% solid.
        alpha = logo_img.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(0.85) # Sedikit transparan
        logo_img.putalpha(alpha)
        
        # 4. Tempelkan Logo ke Gambar Utama (copy agar gambar asli tak rusak)
        branded_img = main_img.copy()
        branded_img.paste(logo_img, (position_x, position_y), logo_img)
        
        # 5. Konversi kembali ke Bytes untuk ditampilkan di Streamlit
        img_byte_arr = io.BytesIO()
        branded_img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
        
    except Exception as e:
        # st.error(f"Gagal integrasi branding: {e}")
        return main_image_bytes # Fallback

# ==============================================================================
# BAGIAN 4: UI/UX STREAMLIT (VERSI BIMBINGAN 4 FINAL)
# ==============================================================================

st.set_page_config(page_title="Inamikro Ad Generator PRO", layout="wide", page_icon="🛍️")

# --- HEADER APLIKASI ---
st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🚀 Inamikro Ad Generator PRO</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Aplikasi Pembuat Konten Iklan Multimodal Berbasis Gemini Pro & Imagen 3 </p>", unsafe_allow_html=True)
st.divider()

if not VERTEX_CONNECTION_SUCCESS:
    st.error("⚠️ Sistem Offline: Gagal terhubung ke GCP Vertex AI. Pastikan Billing aktif.")

# --- INISIALISASI STATE ---
if 'text_result' not in st.session_state: st.session_state.text_result = None
if 'image_result_branded' not in st.session_state: st.session_state.image_result_branded = None
if 'image_prompt' not in st.session_state: st.session_state.image_prompt = None

# --- LAYOUT UTAMA (2 KOLOM SESUAI PROPOSAL 1.2) ---
col_form, col_result = st.columns([1, 1.5], gap="large")

# ---------------------------------------------------------
# KOLOM KIRI: FORM INPUT PENGGUNA
# ---------------------------------------------------------
with col_form:
    st.markdown("### 📋 Langkah 1: Profil UMKM & Branding")
    with st.container(border=True):
        # FITUR REVISI: TAMBAH LOGO UMKM
        logo_umkm = st.file_uploader("Upload Logo UMKM (PNG/JPG)", type=['png', 'jpg', 'jpeg'], help="Akan diintegrasikan di pojok kanan bawah gambar")
        
    st.markdown("### 📝 Langkah 2: Data Produk & Visual Asli")
    with st.container(border=True):
        nama_produk = st.text_input("Nama Produk", placeholder="Contoh: Kopi Senja")
        deskripsi = st.text_area("Deskripsi Produk (USP)", placeholder="Contoh: Kopi aren murni, rasa creamy, harga 15rb.", height=100)
        kategori = st.selectbox("Kategori Usaha KBLI", KBLI_CATEGORIES)
        
        # FITUR REVISI: TAMBAH GAMBAR PRODUK ASLI (MULTIMODAL)
        product_images = st.file_uploader("Upload Foto Asli Produk (Bisa >1)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, help="AI akan menganalisis visual asli produk ini")
        
        # Preview Gambar yang diupload
        if product_images:
            st.markdown("*(Preview Gambar Asli)*")
            cols_preview = st.columns(4)
            for idx, img_file in enumerate(product_images[:4]):
                with cols_preview[idx]:
                    st.image(img_file, use_container_width=True)

    st.markdown("### 🎯 Langkah 3: Strategi Distribusi")
    with st.container(border=True):
        platform = st.radio("Pilih Kanal Platform", ["Instagram (Visual & Feed)", "WhatsApp (Broadcast)", "TikTok (Video AI Script)"])
        gaya = st.selectbox("Gaya Bahasa (Tone)", ["Santai & Kekinian", "Profesional & Elegan", "Promo Hard-Selling"])
        
    st.markdown("<br>", unsafe_allow_html=True)
    btn_generate_text = st.button("🚀 GENERATE DRAFT MULTIMODAL", type="primary", use_container_width=True, disabled=not VERTEX_CONNECTION_SUCCESS)

# ---------------------------------------------------------
# KOLOM KANAN: HASIL OUTPUT
# ---------------------------------------------------------
with col_result:
    st.markdown("### 📱 Langkah 4: Hasil Produksi AI")

    # 1. Eksekusi Generate Teks
    if btn_generate_text:
        if not nama_produk or not deskripsi:
            st.warning("⚠️ Sila isi Nama Produk dan Deskripsi.")
        else:
            st.session_state.image_result_branded = None # Reset gambar lama
            with st.spinner("🧠 Gemini Pro sedang menganalisis Teks & Visual asli..."):
                images_data = [img.getvalue() for img in product_images] if product_images else []
                text_res = generate_ad_text_multimodal(kategori, f"{nama_produk}: {deskripsi}", gaya, platform, images_data)
                st.session_state.text_result = text_res
                st.session_state.image_prompt = parse_output_for_image(text_res)

    # 2. Tampilkan Hasil Teks
    if st.session_state.text_result:
        with st.container(border=True):
            st.markdown(st.session_state.text_result)
            
            st.divider()
            
            # 3. Tombol Generate Gambar (Hanya muncul jika teks sukses)
            if st.session_state.image_prompt:
                st.success("✅ Analisis visual sukses. Siap merender gambar iklan berlogo.")
                btn_image = st.button("🎨 RENDER VISUAL + LOGO POJOK (Imagen 3)", type="primary", use_container_width=True)
                
                if btn_image:
                    with st.spinner("Memproses imej resolusi tinggi (Rasio 1:1)..."):
                        # Generate Gambar Asli dari AI
                        img_raw_bytes = generate_imagen_image(st.session_state.image_prompt)
                        
                        # LOGIKA REVISI: Tempelkan Logo UMKM di pojok kanan bawah
                        if img_raw_bytes and logo_umkm:
                            with st.spinner("Mengintegrasikan Logo (Watermarking)..."):
                                branded_bytes = apply_advanced_branding(img_raw_bytes, logo_umkm)
                                st.session_state.image_result_branded = branded_bytes
                                st.balloons() # Efek balon untuk demo sukses
                        else:
                            st.session_state.image_result_branded = img_raw_bytes # Fallback

    # 4. Tampilkan Hasil Gambar FINAL (Berlogo Pojok)
    if st.session_state.image_result_branded:
        with st.container(border=True):
            st.markdown("#### 🖼️ Hasil Visual Final (AI + Logo Pojok)")
            col_img1, col_img2, col_img3 = st.columns([1, 3, 1])
            with col_img2:
                # Tampilkan Gambar yang sudah berlogo di pojok
                st.image(st.session_state.image_result_branded, use_container_width=True)
                st.download_button(
                    label="⬇️ Download Visual Final", 
                    data=st.session_state.image_result_branded, 
                    file_name="iklan_inamikro_berlogo.png", 
                    mime="image/png", 
                    use_container_width=True
                )

    # Placeholder saat kosong
    if not st.session_state.text_result:
        with st.container(border=True):
            st.info("👈 Silakan isi form di sebelah kiri untuk mulai menghasilkan draf iklan otomatis.")

    # ==============================================================================
    # LANGKAH 5: CHATBOT REVISI (FITUR BARU BAB 3) SESUAI KODINGAN MAS KEVIN
    # ==============================================================================
    if st.session_state.text_result:
        st.markdown("### 🤖 Langkah 5: Asisten Revisi Cepat")
        st.info("Kurang puas dengan hasilnya? Ketik permintaan revisi di bawah (misal: 'Ubah gambar jadi warna gelap' atau 'Ganti gaya bahasanya jadi lebih formal').")
        
        revisi_input = st.chat_input("Ketik instruksi revisi di sini...")
        if revisi_input:
            st.session_state.image_result_branded = None # Reset gambar lama
            with st.spinner("🧠 Gemini Pro sedang memproses revisi Anda..."):
                images_data = [img.getvalue() for img in product_images] if product_images else []
                # Panggil AI lagi, tapi kali ini sertakan instruksi revisi
                new_text_res = generate_ad_text_multimodal(kategori, f"{nama_produk}: {deskripsi}", gaya, platform, images_data, instruksi_revisi=revisi_input)
                
                st.session_state.text_result = new_text_res
                st.session_state.image_prompt = parse_output_for_image(new_text_res)
                st.rerun() # Refresh tampilan otomatis