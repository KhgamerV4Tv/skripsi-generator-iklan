import streamlit as st
import os
import time
from dotenv import load_dotenv
from google import genai # <--- Ini library terbarunya

# ==============================================================================
# KONFIGURASI API KEY (AMAN DARI GITHUB)
# ==============================================================================
load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    # Cara baru memanggil Gemini
    client = genai.Client(api_key=GOOGLE_API_KEY)
    API_SUCCESS = True
except Exception as e:
    API_SUCCESS = False
    st.error(f"Gagal inisialisasi API: {e}")

# ==============================================================================
# SETUP HALAMAN & STATE
# ==============================================================================
st.set_page_config(page_title="Inamikro Ad Generator", page_icon="🚀", layout="wide")

if 'result_text' not in st.session_state: st.session_state.result_text = None
if 'result_image' not in st.session_state: st.session_state.result_image = None

# ==============================================================================
# UI APLIKASI UTAMA
# ==============================================================================
st.title("🚀 Inamikro AI Content Generator")
st.markdown("**Memberdayakan UMKM melalui Pemasaran Digital Berbasis Generative AI**")

if not GOOGLE_API_KEY:
    st.error("⚠️ SISTEM BELUM TERKONEKSI: Pastikan file .env sudah berisi GEMINI_API_KEY.")

# --- LAYOUT KOLOM ---
col_input, col_output = st.columns([1.2, 1.8], gap="large")

with col_input:
    with st.container(border=True):
        st.subheader("📋 Data Produk UMKM")
        nama = st.text_input("Nama Produk/Layanan", placeholder="Contoh: Kopi Senja Gula Aren")
        
        kategori = st.selectbox(
            "Kategori Usaha Inamikro", 
            ["Kuliner (F&B)", "Fashion & Apparel", "Kriya & Kerajinan", "Jasa Pelayanan", "Retail/Toko"]
        )
        
        deskripsi = st.text_area(
            "Deskripsi Produk & USP (Unique Selling Point)", 
            placeholder="Contoh: Kopi susu creamy, menggunakan gula aren organik, harga terjangkau Rp 15.000.",
            height=100
        )
        
        st.subheader("🎯 Strategi Platform")
        platform = st.radio(
            "Pilih Kanal Distribusi:", 
            ["Instagram (Visual & Feed)", "WhatsApp (Direct Broadcast)", "TikTok (Video AI Script)"]
        )
        
        gaya = st.selectbox(
            "Tone of Voice (Gaya Bahasa)", 
            ["Persuasif & Hard-Selling", "Santai & Storytelling", "Profesional & Edukatif"]
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        btn_generate = st.button("✨ GENERATE KONTEN", type="primary", use_container_width=True)

with col_output:
    st.subheader("📱 Hasil Generate AI")
    
    # --- PROSES TEKS ---
    if btn_generate:
        if not nama or not deskripsi:
            st.warning("Mohon isi Nama Produk dan Deskripsi terlebih dahulu.")
        else:
            st.session_state.result_image = None
            
            with st.spinner("🧠 AI sedang menyusun strategi copywriting..."):
                if API_SUCCESS and GOOGLE_API_KEY:
                    
                    if "Instagram" in platform:
                        system_instruction = "Buat caption Instagram estetik, memancing interaksi (engagement), gunakan format paragraf rapi, sertakan 5 hashtag relevan."
                    elif "WhatsApp" in platform:
                        system_instruction = "Buat pesan siaran (broadcast) WhatsApp yang terasa personal, ramah, dan diakhiri dengan Call-to-Action pemesanan."
                    elif "TikTok" in platform:
                        system_instruction = """
                        Buat Naskah Video TikTok yang KOMPATIBEL untuk AI Video Generator (Luma/Runway). 
                        Format wajib:
                        - [PROMPT VISUAL]: Deskripsi detail bahasa Inggris untuk AI video.
                        - [NARASI]: Teks bahasa Indonesia untuk voiceover.
                        Bagi menjadi 3 Scene (Hook, Body, Call to Action).
                        """
                        
                    prompt = f"""
                    Anda adalah Pakar Digital Marketing UMKM.
                    Tugas: {system_instruction}
                    Konteks Bisnis:
                    - Nama Produk: {nama}
                    - Kategori Usaha: {kategori}
                    - Detail/USP: {deskripsi}
                    - Gaya Bahasa: {gaya}
                    Langsung berikan output dalam format Markdown.
                    """
                    
                    try:
                        # Cara baru melakukan generate text (SDK Terbaru)
                        response = client.models.generate_content(
                            model='gemini-2.5-pro',
                            contents=prompt
                        )
                        st.session_state.result_text = response.text
                    except Exception as e:
                        st.error(f"Koneksi AI Gagal: {e}")
                else:
                    st.error("API Key belum disetting dengan benar.")
    
    # --- TAMPILAN OUTPUT ---
    if st.session_state.result_text:
        with st.container(border=True):
            st.markdown(st.session_state.result_text)
            st.divider()
            
            st.caption("Visualisasi Produk (Simulasi Imagen 3)")
            col_img_btn, _ = st.columns([1, 1])
            with col_img_btn:
                btn_image = st.button("🎨 Buat Ilustrasi Visual (Rasio 1:1)", type="secondary", use_container_width=True)
            
            if btn_image:
                with st.spinner("Memproses text-to-image synthesis..."):
                    time.sleep(2) 
                    st.session_state.result_image = True
        
        if st.session_state.result_image:
            with st.container(border=True):
                st.success("✅ Visual berhasil dibuat!")
                st.image(
                    "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?q=80&w=500&auto=format&fit=crop", 
                    caption=f"Visual Generated for: {nama}", 
                    width=400
                )