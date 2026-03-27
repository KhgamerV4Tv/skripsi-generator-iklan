import streamlit as st
import google.generativeai as genai
import time

# ==============================================================================
# KONFIGURASI API KEY
# ==============================================================================
# Masukkan API Key Google AI Studio (Gemini 1.5 Pro / 2.5 Pro)
GOOGLE_API_KEY = "AIzaSyApap9IwaQ8jtr72gNaIaT-cqRXD1HLA38" 

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    # Menggunakan model terbaru sesuai proposal
    model = genai.GenerativeModel('gemini-2.5-pro') 
    API_SUCCESS = True
except:
    API_SUCCESS = False

# ==============================================================================
# SETUP HALAMAN & STATE
# ==============================================================================
st.set_page_config(page_title="Inamikro Ad Generator", page_icon="🚀", layout="wide")

if 'result_text' not in st.session_state: st.session_state.result_text = None
if 'result_image' not in st.session_state: st.session_state.result_image = None
if 'platform_choice' not in st.session_state: st.session_state.platform_choice = None

# ==============================================================================
# UI APLIKASI UTAMA
# ==============================================================================
st.title("🚀 Inamikro AI Content Generator")
st.markdown("**Memberdayakan UMKM melalui Pemasaran Digital Berbasis Generative AI**")

if GOOGLE_API_KEY == "MASUKKAN_API_KEY_ANDA_DI_SINI":
    st.error("⚠️ SISTEM BELUM TERKONEKSI: Masukkan API Key Google Vertex AI/AI Studio Anda di baris ke-9.")

# --- LAYOUT KOLOM ---
col_input, col_output = st.columns([1.2, 1.8], gap="large")

with col_input:
    with st.container(border=True):
        st.subheader("📋 Data Produk UMKM")
        nama = st.text_input("Nama Produk/Layanan", placeholder="Contoh: Kopi Senja Gula Aren")
        
        # Sesuai Proposal: Basis Kategori KBLI
        kategori = st.selectbox(
            "Kategori Usaha Inamikro", 
            ["Kuliner (F&B)", "Fashion & Apparel", "Kriya & Kerajinan", "Jasa Pelayanan", "Retail/Toko"]
        )
        
        # Sesuai Proposal: Unique Selling Point (USP)
        deskripsi = st.text_area(
            "Deskripsi Produk & USP (Unique Selling Point)", 
            placeholder="Contoh: Kopi susu creamy, menggunakan gula aren organik, harga terjangkau Rp 15.000, cocok untuk teman kerja.",
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
            st.session_state.result_image = None # Reset gambar
            st.session_state.platform_choice = platform
            
            with st.spinner("🧠 AI sedang menyusun strategi copywriting..."):
                if API_SUCCESS and GOOGLE_API_KEY != "MASUKKAN_API_KEY_ANDA_DI_SINI":
                    
                    # LOGIKA DYNAMIC PROMPTING (Sesuai Bab 1.2 & Bab 3)
                    if "Instagram" in platform:
                        system_instruction = "Buat caption Instagram yang estetik, memancing interaksi (engagement), gunakan format paragraf yang rapi, dan sertakan minimal 5 hashtag yang relevan."
                    elif "WhatsApp" in platform:
                        system_instruction = "Buat pesan siaran (broadcast) WhatsApp yang terasa personal, ramah, dan diakhiri dengan Call-to-Action (CTA) berupa link/nomor untuk pemesanan."
                    elif "TikTok" in platform:
                        system_instruction = """
                        Buat Naskah Video TikTok yang KOMPATIBEL untuk diinput ke AI Video Generator (seperti Luma Dream Machine atau Runway Gen-2). 
                        Format wajib:
                        - [PROMPT VISUAL UNTUK AI]: Deskripsi sangat detail dalam bahasa Inggris untuk digenerate menjadi video.
                        - [NARASI/VOICEOVER]: Teks bahasa Indonesia yang diucapkan oleh kreator/AI Voice.
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
                    
                    Langsung berikan hasil akhirnya dalam format Markdown tanpa basa-basi.
                    """
                    
                    try:
                        response = model.generate_content(prompt)
                        st.session_state.result_text = response.text
                    except Exception as e:
                        st.error(f"Koneksi AI Gagal: {e}")
                else:
                    # Simulasi jika API Key belum dipasang
                    time.sleep(2)
                    st.session_state.result_text = f"""
                    *(Ini adalah mode simulasi. Pasang API Key untuk hasil asli)*
                    ### Naskah {platform} untuk {nama}
                    Berhasil merancang strategi untuk kategori {kategori} dengan gaya {gaya}.
                    """
    
    # --- TAMPILAN OUTPUT ---
    if st.session_state.result_text:
        with st.container(border=True):
            st.markdown(st.session_state.result_text)
            
            st.divider()
            
            # --- TOMBOL GAMBAR (IMAGEN 3) ---
            st.caption("Visualisasi Produk (Simulasi Imagen 3)")
            col_img_btn, _ = st.columns([1, 1])
            with col_img_btn:
                btn_image = st.button("🎨 Buat Ilustrasi Visual (Rasio 1:1)", type="secondary", use_container_width=True)
            
            if btn_image:
                with st.spinner("Memproses text-to-image synthesis..."):
                    time.sleep(2) 
                    st.session_state.result_image = True
        
        # --- TAMPILAN GAMBAR ---
        if st.session_state.result_image:
            with st.container(border=True):
                st.success("✅ Visual berhasil dibuat!")
                # Simulasi hasil Imagen 3 (Rasio 1:1 Square sesuai proposal)
                st.image(
                    "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?q=80&w=500&auto=format&fit=crop", 
                    caption=f"Visual Generated for: {nama}", 
                    width=400
                )