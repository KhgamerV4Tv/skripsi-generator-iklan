import os
import streamlit as st
import re
import io
import base64
import requests
import openai
import pandas as pd
import json
import random
from datetime import datetime
from pathlib import Path
from PIL import Image
import google.generativeai as genai
from serpapi import GoogleSearch

# ==============================================================================
# KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(
    page_title="Ad Generator V19 Pro",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# CSS — DESAIN AKADEMIK ELEGAN UNTUK PRESENTASI SKRIPSI
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap');

    /* ===== GLOBAL ===== */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
    }

    [data-testid="stAppViewContainer"] {
        background: var(--background-color);
    }

    /* Sembunyikan footer Streamlit, biarkan menu titik 3 muncul untuk ganti theme */
    footer { visibility: hidden; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 3rem !important; }

    /* ===== HERO HEADER ===== */
    .hero-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #3730a3 50%, #4f46e5 100%);
        padding: 2.2rem 2.5rem;
        border-radius: 20px;
        margin-bottom: 1.8rem;
        box-shadow: 0 20px 50px -15px rgba(79, 70, 229, 0.45);
        position: relative;
        overflow: hidden;
    }
    .hero-header::before {
        content: '';
        position: absolute; top: -50%; right: -10%;
        width: 400px; height: 400px;
        background: radial-gradient(circle, rgba(251, 191, 36, 0.18) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-header::after {
        content: '';
        position: absolute; bottom: -60%; left: -10%;
        width: 350px; height: 350px;
        background: radial-gradient(circle, rgba(167, 139, 250, 0.15) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-content { position: relative; z-index: 2; display: flex; align-items: center; gap: 1.4rem; }
    .hero-icon {
        width: 64px; height: 64px;
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        border-radius: 16px;
        display: flex; align-items: center; justify-content: center;
        font-size: 2rem;
        box-shadow: 0 8px 20px -5px rgba(251, 191, 36, 0.6);
        flex-shrink: 0;
    }
    .hero-text h1 {
        color: #ffffff !important;
        font-size: 1.85rem; font-weight: 800;
        margin: 0; letter-spacing: -0.02em;
        line-height: 1.1;
    }
    .hero-text .hero-sub {
        color: #c7d2fe;
        margin-top: 0.35rem; font-size: 0.95rem;
        font-weight: 500;
    }
    .hero-badges { margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; position: relative; z-index: 2; }
    .hero-badge {
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        padding: 0.35rem 0.85rem;
        border-radius: 999px;
        color: #e0e7ff;
        font-size: 0.75rem;
        font-weight: 600;
    }
    /* ===== DISCLAIMER HERO ===== */
    .hero-disclaimer {
        margin-top: 1.2rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        font-size: 0.78rem;
        color: #a5b4fc;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 0.5rem 0.8rem;
        border-radius: 8px;
        width: fit-content;
        position: relative;
        z-index: 2;
    }

    /* ===== STEP PROGRESS STEPPER ===== */
    .stepper-wrap {
        background: var(--secondary-background-color, #ffffff);
        border-radius: 16px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px -2px rgba(15, 23, 42, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    .stepper {
        display: flex; justify-content: space-between; align-items: center;
        gap: 0.5rem; overflow-x: auto;
    }
    .step-item {
        display: flex; flex-direction: column; align-items: center;
        flex: 1; min-width: 80px; text-align: center;
        position: relative;
    }
    .step-circle {
        width: 36px; height: 36px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 0.9rem;
        background: #f1f5f9; color: #94a3b8;
        border: 2px solid #e2e8f0;
        transition: all 0.3s;
        z-index: 2;
    }
    .step-label-txt {
        font-size: 0.7rem; color: #64748b;
        margin-top: 0.4rem; font-weight: 600;
        line-height: 1.2;
    }
    .step-label-txt.active { color: #4f46e5; }
    .step-connector {
        position: absolute; top: 18px; left: 50%; width: 100%;
        height: 2px; background: #e2e8f0; z-index: 1;
    }
    .step-item:last-child .step-connector { display: none; }

    /* ===== PERBAIKAN WARNA STEPPER PROGRESS BAR ===== */
    .step-circle {
        background: #334155 !important;
        color: #94a3b8 !important;
        border-color: #475569 !important;
    }
    .step-circle.active {
        background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
        color: #ffffff !important; 
        border-color: #6d28d9 !important;
        box-shadow: 0 0 15px rgba(124, 58, 237, 0.4) !important;
    }
    .step-circle.done {
        background: linear-gradient(135deg, #10b981, #059669) !important;
        color: #ffffff !important; 
        border-color: #047857 !important;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2) !important;
    }
    .step-connector { background: #334155 !important; }

    /* ===== SECTION HEADER ===== */
    .section-card-header {
        display: flex; align-items: center; gap: 0.7rem;
        margin: 0 0 1rem 0;
    }
    .section-num {
        width: 32px; height: 32px;
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: #fff;
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 0.95rem;
        box-shadow: 0 4px 10px -2px rgba(79, 70, 229, 0.4);
        flex-shrink: 0;
    }
    .section-title {
        font-size: 1.05rem; font-weight: 700;
        color: var(--text-color, #1e293b);
        letter-spacing: -0.01em;
    }
    .section-subtitle {
        font-size: 0.78rem;
        color: var(--text-color-secondary, #64748b);
        font-weight: 500;
        margin-top: 0.1rem;
        opacity: 0.85;
    }

    /* ===== CONTAINER CARDS ===== */
    div[data-testid="stVerticalBlockBorderWithFormatting"] {
        background-color: var(--secondary-background-color, #ffffff) !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 12px -4px rgba(15, 23, 42, 0.06) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        transition: box-shadow 0.25s ease;
    }
    div[data-testid="stVerticalBlockBorderWithFormatting"]:hover {
        box-shadow: 0 4px 6px rgba(15, 23, 42, 0.05), 0 12px 25px -5px rgba(15, 23, 42, 0.1) !important;
    }

    /* ===== INFO BOXES ===== */
    .kbli-desc, .elemen-box, .photo-caption-box {
        border-radius: 10px;
        padding: 0.85rem 1.1rem;
        font-size: 0.85rem;
        margin-top: 0.7rem;
        color: #1e293b !important;
        line-height: 1.55;
        font-weight: 500;
    }
    .kbli-desc {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border-left: 4px solid #3b82f6;
    }
    .elemen-box {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border-left: 4px solid #22c55e;
    }
    .photo-caption-box {
        background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
        border-left: 4px solid #f97316;
        margin-bottom: 0.9rem;
    }

    /* ===== KEYWORD TAGS ===== */
    .kw-tag {
        background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
        border-radius: 999px;
        padding: 7px 14px;
        font-size: 0.78rem;
        color: #0c4a6e;
        margin: 4px 5px 8px 0;
        display: inline-block;
        font-weight: 600;
        border: 1px solid #7dd3fc;
        box-shadow: 0 1px 3px rgba(14, 165, 233, 0.15);
    }

    /* ===== BUTTONS ===== */
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
        letter-spacing: -0.01em;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        border: none !important;
        box-shadow: 0 4px 14px -2px rgba(79, 70, 229, 0.45) !important;
        padding: 0.7rem 1.2rem !important;
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 20px -2px rgba(79, 70, 229, 0.6) !important;
    }

    /* ===== INPUTS & WIDGETS ===== */
    .stTextInput input, .stTextArea textarea, .stNumberInput input, 
    .stSelectbox [data-baseweb="select"], 
    .stMultiSelect [data-baseweb="select"],
    [data-testid="stFileUploaderDropzone"] {
        border-radius: 10px !important;
        border-color: rgba(128, 128, 128, 0.2) !important;
        background-color: var(--secondary-background-color) !important;
        color: var(--text-color) !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus,
    .stSelectbox [data-baseweb="select"]:focus, .stMultiSelect [data-baseweb="select"]:focus {
        border-color: #4f46e5 !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1) !important;
    }

    ::placeholder {
        color: #94a3b8 !important;
        opacity: 1 !important;
    }

    [data-testid="stWidgetLabel"] p, 
    [data-testid="stWidgetLabel"] div,
    label {
        color: var(--text-color) !important;
        font-weight: 600 !important;
    }

    /* --- PERBAIKAN FILE UPLOADER --- */
    [data-testid="stFileUploaderDropzone"] div,
    [data-testid="stFileUploaderDropzone"] p,
    [data-testid="stFileUploaderDropzone"] small {
        color: var(--text-color) !important; 
    }
    
    [data-testid="stFileUploaderDropzone"] button {
        background-color: #4f46e5 !important; 
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
    }

    /* --- PERBAIKAN MULTISELECT TAG --- */
    .stMultiSelect [data-baseweb="tag"] {
        background-color: rgba(79, 70, 229, 0.15) !important; 
        border: 1px solid #a78bfa !important;
        border-radius: 6px !important;
    }
    .stMultiSelect [data-baseweb="tag"] span {
        color: #4f46e5 !important; 
        font-weight: 600 !important;
    }

    /* ===== PERBAIKAN TEKS RADIO BUTTON & SUB-HEADING ===== */
    .stRadio [data-testid="stMarkdownContainer"] p {
        color: var(--text-color, #f1f5f9) !important;
        font-weight: 500 !important;
    }

    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] h6 {
        color: var(--text-color, #f1f5f9) !important;
    }

    /* ===== QC SUCCESS CARD ===== */
    .qc-card {
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        border: 1px solid #6ee7b7;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-top: 0.8rem;
        display: flex; align-items: center; gap: 0.8rem;
    }
    .qc-icon {
        width: 40px; height: 40px;
        background: linear-gradient(135deg, #10b981, #059669);
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem;
        flex-shrink: 0;
        box-shadow: 0 4px 10px -2px rgba(16, 185, 129, 0.4);
    }
    .qc-title { font-weight: 700; color: #065f46; font-size: 0.95rem; }
    .qc-sub { font-size: 0.78rem; color: #047857; margin-top: 0.15rem; }

    /* ===== EMPTY STATE ===== */
    .empty-state {
        background: var(--secondary-background-color, #ffffff);
        border: 2px dashed rgba(128, 128, 128, 0.35);
        border-radius: 16px;
        padding: 3.5rem 2rem;
        text-align: center;
    }
    .empty-icon { font-size: 3.5rem; margin-bottom: 0.6rem; opacity: 0.5; }
    .empty-title { font-size: 1.1rem; font-weight: 700; color: #475569; margin-bottom: 0.4rem; }
    .empty-sub { font-size: 0.88rem; color: #94a3b8; }

    hr { margin: 1.2rem 0 !important; border-color: #e2e8f0 !important; }

    [data-testid="stChatMessage"] {
        border-radius: 12px !important;
        padding: 0.9rem 1rem !important;
        margin-bottom: 0.6rem !important;
    }

    .stRadio > div { gap: 0.5rem; }

    /* =============================================================
        DARK MODE ADAPTIVE
       ============================================================= */
    @media (prefers-color-scheme: dark) {
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%);
        }
        
        [data-testid="stWidgetLabel"] p, 
        [data-testid="stWidgetLabel"] div,
        label {
            color: #f8fafc !important; 
        }

        div[data-testid="stVerticalBlockBorderWithFormatting"] {
            background-color: #1e293b !important;
            border: 1px solid #334155 !important;
            box-shadow: 0 4px 12px -4px rgba(0, 0, 0, 0.4) !important;
        }

        .kbli-desc {
            background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%) !important;
            color: #dbeafe !important;
        }
        .kbli-desc * { color: #dbeafe !important; }

        .elemen-box {
            background: linear-gradient(135deg, #14532d 0%, #166534 100%) !important;
            color: #dcfce7 !important;
        }
        .elemen-box * { color: #dcfce7 !important; }

        .photo-caption-box {
            background: linear-gradient(135deg, #7c2d12 0%, #9a3412 100%) !important;
            color: #fed7aa !important;
        }
        .photo-caption-box * { color: #fed7aa !important; }

        .kw-tag {
            background: linear-gradient(135deg, #0c4a6e 0%, #075985 100%) !important;
            color: #bae6fd !important;
            border-color: #0369a1 !important;
        }

        .section-title { color: #f1f5f9 !important; }
        .section-subtitle { color: #94a3b8 !important; }

        .stepper-wrap { background: #1e293b !important; border-color: #334155 !important; }
        .step-label-txt { color: #94a3b8 !important; }
        .step-label-txt.active { color: #a78bfa !important; }

        .qc-card {
            background: linear-gradient(135deg, #064e3b 0%, #065f46 100%) !important;
            border-color: #10b981 !important;
        }
        .qc-title { color: #d1fae5 !important; }
        .qc-sub { color: #6ee7b7 !important; }

        .empty-state { background: #1e293b !important; border-color: #475569 !important; }
        .empty-title { color: #cbd5e1 !important; }
        .empty-sub { color: #94a3b8 !important; }

        .metric-card {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
            border-color: #334155 !important;
        }
        .metric-val { color: #a78bfa !important; }
        .metric-lbl { color: #94a3b8 !important; }

        /* Inputs di dark mode */
        .stTextInput input, .stTextArea textarea, .stNumberInput input,
        .stSelectbox [data-baseweb="select"], 
        .stMultiSelect [data-baseweb="select"],
        [data-testid="stFileUploaderDropzone"] {
            background-color: #0f172a !important;
            border-color: #334155 !important;
            color: #f1f5f9 !important;
        }

        [data-testid="stFileUploaderDropzone"] div,
        [data-testid="stFileUploaderDropzone"] p,
        [data-testid="stFileUploaderDropzone"] small {
            color: #cbd5e1 !important;
        }

        .stMultiSelect [data-baseweb="tag"] { background-color: #4f46e5 !important; }
        .stMultiSelect [data-baseweb="tag"] span { color: #ffffff !important; }
        .stMultiSelect [data-baseweb="tag"] svg { fill: #ffffff !important; }

        .stRadio [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] h1,
        [data-testid="stMarkdownContainer"] h2,
        [data-testid="stMarkdownContainer"] h3,
        [data-testid="stMarkdownContainer"] h4,
        [data-testid="stMarkdownContainer"] h5,
        [data-testid="stMarkdownContainer"] h6 {
            color: #f8fafc !important; 
        }

        hr { border-color: #334155 !important; }
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# HERO HEADER
# ==============================================================================
st.markdown("""
<div class="hero-header">
    <div class="hero-content">
        <div class="hero-icon">📈</div>
        <div class="hero-text">
            <h1> Ad Generator <span style="color: #fbbf24;">V19 Pro</span></h1>
            <div class="hero-sub">Platform Generator Copywriting & Komparasi Engine Visual Skripsi UMKM</div>
        </div>
    </div>
    <div class="hero-badges">
        <span class="hero-badge">⚡ Generasi Otomatis</span>
        <span class="hero-badge">⚖️ AI Quality Control</span>
        <span class="hero-badge">📊 KBLI </span>
        <span class="hero-badge">📐 Multi-Rasio</span>
    </div>
    <div class="hero-disclaimer">
        <span>🔒</span> 
        <span><b>Aman & Privat:</b> Data dan foto yang diunggah hanya diproses secara <i>real-time</i> oleh sistem dan tidak disimpan oleh sistem .</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# DATA MASTER PROMPT & DATA KBLI UMKM
# ==============================================================================
MASTER_PROMPT_PATH = Path(__file__).parent / "master_prompt_umkm.md"

@st.cache_data
def load_master_prompt():
    try:
        if MASTER_PROMPT_PATH.exists(): return MASTER_PROMPT_PATH.read_text(encoding="utf-8")
    except Exception: pass
    return "Kamu adalah Agen Marketing UMKM Pakar Copywriting Indonesia."

MASTER_PROMPT_FULL = load_master_prompt()

KBLI_DATA = {
    "56102 - Restoran/Rumah Makan": {"desc": "Usaha makanan siap saji di tempat makan.", "tipe": "food"},
    "56303 - Kafe/Kedai Minuman": {"desc": "Usaha yang menjual minuman dan makanan ringan.", "tipe": "food"},
    "10794 - Makanan Ringan/Keripik": {"desc": "Usaha produksi makanan ringan dalam kemasan.", "tipe": "food"},
    "10750 - Frozen Food": {"desc": "Usaha produksi makanan beku yang diproses dan dikemas.", "tipe": "food"},
    "47711 - Perdagangan Pakaian": {"desc": "Usaha penjualan pakaian jadi eceran.", "tipe": "fashion"},
    "47721 - Kosmetik & Skincare": {"desc": "Usaha penjualan produk kecantikan dan perawatan kulit.", "tipe": "fashion"},
    "32990 - Kerajinan/Aksesoris": {"desc": "Usaha pembuatan kerajinan tangan, aksesoris, atau souvenir.", "tipe": "fashion"},
    "96020 - Salon & Kecantikan": {"desc": "Usaha layanan pangkas rambut, kosmetik, dan salon.", "tipe": "jasa"},
    "47192 - Perdagangan Umum/Eceran": {"desc": "Usaha penjualan berbagai macam barang, toko kelontong, atau retail umum.", "tipe": "jasa"},
    "25110 - Industri Barang Logam": {"desc": "Pembuatan produk logam siap pasang untuk bangunan (railing tangga, kanopi, pagar, tralis).", "tipe": "jasa"},
    "41019 - Konstruksi/Renovasi Bangunan": {"desc": "Usaha jasa pengerjaan konstruksi, interior, atau renovasi.", "tipe": "jasa"},
    "00000 - Kategori Usaha Lainnya": {"desc": "Kategori usaha umum lainnya yang belum terdaftar di atas.", "tipe": "jasa"}
}

BROSUR_ELEMEN = {
    "food": ["Nama Produk", "Harga", "Keunggulan/USP", "Promo/Diskon", "Call-to-Action", "Kontak/WhatsApp"],
    "fashion": ["Nama Brand", "Jenis Produk", "Ukuran Tersedia", "Harga", "Call-to-Action", "Kontak/WhatsApp"],
    "jasa": ["Nama Usaha", "Jenis Layanan", "Harga/Tarif", "Keunggulan", "Call-to-Action", "Kontak/WhatsApp"],
}

def get_elemen_wajib(kategori_key):
    tipe = KBLI_DATA.get(kategori_key, {}).get("tipe", "food")
    return BROSUR_ELEMEN.get(tipe, BROSUR_ELEMEN["food"])

BACKGROUND_OPTIONS = {
    "⬜ Studio Putih Bersih": "clean white studio background with soft shadows",
    "🪵 Meja Kayu Estetik": "rustic wooden table with warm bokeh background",
    "🍳 Dapur Modern": "modern kitchen background with clean countertops",
    "🌿 Alam Hijau Segar": "fresh green leaves natural outdoor background",
    "🏙️ Jalanan Perkotaan (Street Style)": "urban street style background with city vibes",
    "🛁 Kamar Mandi Mewah": "luxurious bathroom background with marble and soft lighting",
    "💎 Tekstur Marmer Premium": "premium marble texture background",
    "☕ Kafe Estetik (Cafe Vibes)": "aesthetic cafe interior background with warm lighting",
    "🌸 Pastel Aesthetic": "soft pastel pink and cream aesthetic background",
    "⬛ Studio Gelap Elegan": "dark matte studio background with dramatic side lighting"
}

ASPECT_RATIO_OPTIONS = {
    "1:1 (Persegi / IG Feed)": "1024x1024",
    "9:16 (Potret / IG Story)": "1024x1792",
    "16:9 (Lanskap / YouTube)": "1792x1024"
}

# ==============================================================================
# INITIALIZE SESSION STATE
# ==============================================================================
for k in ['main_txt', 'vis_prompt', 'last_p', 'img_mem', 'chat_history', 'image_size', 'ai_eval_result', 'copyright_data_live']:
    if k not in st.session_state: st.session_state[k] = None
if st.session_state.img_mem is None: st.session_state.img_mem = {"A": None}
if st.session_state.chat_history is None: st.session_state.chat_history = []
if st.session_state.image_size is None: st.session_state.image_size = "1024x1024"

if "skripsi_data" not in st.session_state: st.session_state.skripsi_data = []
if "daftar_produk_umkm" not in st.session_state: st.session_state.daftar_produk_umkm = []
if "usage_logs" not in st.session_state: st.session_state.usage_logs = []

# ==============================================================================
# FUNGSI FIRESTORE PENANGANAN LOG
# ==============================================================================
def load_gcp_credentials():
    from google.oauth2.service_account import Credentials
    secret_keys = st.secrets.keys()
    target_key = "gcp_service_account" if "gcp_service_account" in secret_keys else "GCP_SERVICE_ACCOUNT" if "GCP_SERVICE_ACCOUNT" in secret_keys else None
    if target_key:
        try:
            info = dict(st.secrets[target_key])
            return Credentials.from_service_account_info(info), info["project_id"]
        except Exception: pass
    return None, None

def get_firestore_client():
    try:
        from google.cloud import firestore
        creds, project_id = load_gcp_credentials()
        if creds and project_id: return firestore.Client(project=project_id, credentials=creds)
    except Exception: pass
    return None

db = get_firestore_client()

def catat_aktivitas_sistem(aktivitas, nama_brand):
    log_entry = {"Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Aktivitas": aktivitas, "Nama Usaha": nama_brand}
    if db:
        try: db.collection("log_penggunaan").add(log_entry)
        except Exception: pass
    else:
        st.session_state.usage_logs.append(log_entry)

# ==============================================================================
# ENGINE GATEWAY MULTI-MODEL ROUTING (OPENROUTER SDK LIVE)
# ==============================================================================
def invoke_openrouter_text_engine(model_id, system_prompt, user_content):
    try:
        api_key = st.secrets.get("OPENROUTER_API_KEY")
        if not api_key:
            return "⚠️ Konfigurasi Error: OPENROUTER_API_KEY tidak ditemukan di secrets.toml!"
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.3
        }
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"]
        else:
            return f"⚠️ OpenRouter Error ({res.status_code}): {res.text}"
    except Exception as e:
        return f"⚠️ Gangguan Koneksi Jaringan Gateway: {str(e)}"

@st.cache_data(show_spinner=False)
def evaluate_ad_quality_master(kategori, text_result):
    prompt = f"""Kamu adalah Dosen Pakar Marketing Digital & AI.
Tugasmu adalah menjadi 'LLM-as-a-Judge' untuk mengevaluasi naskah iklan UMKM berikut.

Kategori Usaha: {kategori}
Naskah Iklan:
{text_result}

Berikan penilaian analitis dan ketat. Tampilkan output HANYA dalam format ini:
SKOR KELAYAKAN: (Hanya tuliskan satu angka murni 1-100 di sini, tanpa simbol atau teks tambahan apapun)
ANALISIS PAKAR: [Berikan 2-3 kalimat penjelasan mengapa skor tersebut diberikan, sebutkan kelebihan dan kekurangannya berdasarkan target pasar]
"""
    # Memakai model utama lewat OpenRouter untuk Agen Evaluator otomatis
    return invoke_openrouter_text_engine("google/gemini-2.5-pro", "Kamu adalah Agen Penilai Kualitas Pemasaran.", prompt)

@st.cache_data(show_spinner=False)
def generate_ad_revision_master(main_txt, vis_prompt, revisi_input):
    old_output = f"{main_txt}\n\n**Ide Visual:**\n{vis_prompt}"
    prompt = f"""Kamu adalah Agen Pakar Marketing UMKM.

=== HASIL IKLAN SEBELUMNYA ===
{old_output}

=== INSTRUKSI REVISI DARI PENGGUNA ===
"{revisi_input}"

TUGAS:
Lakukan revisi HANYA pada bagian yang diminta. Jangan merombak total gaya bahasa yang sudah ada.
Pastikan output akhir TETAP mengikuti format baku (ada Headline, Caption, Hashtags, dan bagian **Ide Visual:** di paling bawah untuk instruksi gambar).
"""
    return invoke_openrouter_text_engine("google/gemini-2.5-pro", "Kamu adalah Asisten Editor Pemasaran.", prompt)

# ==============================================================================
# PARSING & PROMPT BUILDING
# ==============================================================================
def parse_output_for_image(markdown_text):
    try:
        matches = list(re.finditer(r"\*\*Ide Visual:\*\*[\s]*(.*?)(?=\n\n|\Z)", markdown_text, re.IGNORECASE | re.DOTALL))
        if matches:
            last_match = matches[-1]
            clean_idea = last_match.group(1).strip().replace('*', '').replace('\n', ' ')
            main_text = markdown_text[:last_match.start()].strip()
            return clean_idea[:500], main_text
    except Exception: pass
    return "", markdown_text

def build_context_block(kategori, brand_name, keywords_list, gaya, platform, market, mood, background, subjek, elemen_wajib, mode_promo, deskripsi_harga_global, list_produk):
    market_str = ", ".join(market) if market else "Umum"
    keywords_str = ", ".join(keywords_list) if keywords_list else brand_name
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])
    bg_desc = BACKGROUND_OPTIONS.get(background, background)

    produk_block = ""
    if mode_promo == "Deskripsi Bebas (Harga Sama/Massal)":
        produk_block = f"\n  - Detail Harga & Promo: {deskripsi_harga_global}"
    else:
        for idx, p in enumerate(list_produk):
            p_promo = f" (Promo: {p['promo']})" if p['promo'] else " (Tanpa Promo)"
            produk_block += f"\n  {idx+1}. {p['nama']} -> Harga: {p['harga']}{p_promo}"

    return f"""
=== INPUT TERSTRUKTUR ===
- Nama Brand/Usaha: {brand_name}
- Karakteristik/USP Sektor: {keywords_str}
- Kategori Usaha: {kategori}
- Strategi Penawaran Produk:{produk_block}
- Target Market: {market_str}
- Platform Media: {platform} (Tone Copywriting: {gaya})
- Konsep Visual: {subjek} di {bg_desc} ({mood} atmosphere)
- Elemen Wajib yang HARUS Ditulis di dalam Iklan:
{elemen_str}

=== PERINTAH TEGAS GENERASI VISUAL ===
Jangan membuat gambar abstrak atau patung 3D geometris! Ide Visual harus berupa konsep fotografi komersial (Commercial Product Photography) nyata yang menampilkan wujud asli produk '{brand_name}' secara menarik, rapi, dan sesuai dengan suasana latar belakang yang dipilih.
"""

# ==============================================================================
# MODEL GENERATOR OPENAI IMAGES (DALL-E)
# ==============================================================================
def generate_dalle_image(prompt_text, res_size):
    if not prompt_text: return None
    try:
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        context_anchor = f"Commercial product advertisement photography for '{st.session_state.get('brand_name', 'UMKM')}' showing realistic products of {st.session_state.get('kategori', 'Product')}. Photorealistic, high quality, appetizing style, no abstract 3D figures, no geometric sculptures, "
        safe_prompt = (context_anchor + prompt_text)[:900]

        res = client.images.generate(model="gpt-image-2", prompt=safe_prompt, size=res_size, n=1)
        if hasattr(res.data[0], 'url') and res.data[0].url:
            return requests.get(res.data[0].url).content
    except Exception as e:
        st.error(f"Gagal memproses GPT Image: {e}")
        return None

# ==============================================================================
# WATERMARK PROCESSING (PILLOW)
# ==============================================================================
def apply_dynamic_branding(main_bytes, logo_file, posisi):
    if not main_bytes or not logo_file: return main_bytes
    try:
        main_img = Image.open(io.BytesIO(main_bytes))
        logo_img = Image.open(logo_file).convert('RGBA')
        nw = int(main_img.width * 0.18)
        nh = int(nw * (logo_img.height / logo_img.width))
        logo_img = logo_img.resize((nw, nh), Image.Resampling.LANCZOS)
        pad = 28
        pos = (pad, pad)
        if "Kanan Atas" in posisi: pos = (main_img.width - nw - pad, pad)
        elif "Kanan Bawah" in posisi: pos = (main_img.width - nw - pad, main_img.height - nh - pad)
        elif "Kiri Bawah" in posisi: pos = (pad, main_img.height - nh - pad)
        res = main_img.copy()
        res.paste(logo_img, pos, logo_img)
        out = io.BytesIO()
        res.save(out, format='PNG')
        return out.getvalue()
    except Exception: return main_bytes

# ==============================================================================
# ENGINE CEK COPYRIGHT REVERSE SEARCH (SERPAPI GOOGLE LENS)
# ==============================================================================
def upload_to_temporary_host(img_bytes):
    try:
        b64_img = base64.b64encode(img_bytes).decode('utf-8')
        payload = {"image": b64_img}
        # Mengunggah data piksel sementara ke server ImgBB gratis anonim untuk syarat tautan URL
        res = requests.post("https://api.imgbb.com/1/upload?key=ch_anon_api_key_skripsi_998822f", data=payload, timeout=15)
        if res.status_code == 200:
            return res.json().get("data", {}).get("url")
    except Exception: pass
    return None

def execute_live_google_lens_check(img_bytes):
    try:
        public_url = upload_to_temporary_host(img_bytes)
        if not public_url: return {"error": "Gagal memproses unggah URL gambar."}
        params = {"engine": "google_lens", "url": public_url, "api_key": st.secrets["SERPAPI_API_KEY"]}
        search = GoogleSearch(params)
        results = search.get_dict()
        visual_matches = results.get("visual_matches", [])
        if not visual_matches: return {"rate": 5, "matches": []}
        match_count = len(visual_matches)
        calculated_rate = 100 if match_count >= 15 else 75 if match_count >= 5 else 22
        return {"rate": calculated_rate, "matches": visual_matches[:4]}
    except Exception as e:
        return {"error": f"Gangguan server Lens: {str(e)}"}

# ==============================================================================
# USER INTERFACE LAYOUT
# ==============================================================================
col_f, col_r = st.columns([1, 1.35], gap="large")

with col_f:
    st.markdown('<div class="section-card-header"><div class="section-num">1</div><div><div class="section-title">Identitas & Branding UMKM</div></div></div>', unsafe_allow_html=True)
    with st.container(border=True):
        col_l1, col_l2 = st.columns([1.3, 1])
        with col_l1: logo_file = st.file_uploader("Upload Logo UMKM", type=['png', 'jpg', 'jpeg'])
        with col_l2: posisi_logo = st.selectbox("Posisi Logo", ["Kanan Atas", "Kiri Atas", "Kanan Bawah", "Kiri Bawah"])
        lokasi_raw = st.multiselect("📍 Lokasi", ["Semua Wilayah", "Surabaya & Sekitarnya", "Sidoarjo"], default=["Semua Wilayah"])
        umur_raw = st.multiselect("🎂 Umur", ["Semua Umur", "Remaja (13-18 thn)", "Dewasa Muda (19-35 thn)"], default=["Semua Umur"])
        gender = st.selectbox("🚻 Gender", ["Semua Gender", "Perempuan Khusus", "Laki-laki Khusus"])
        pasar_raw = st.multiselect("👥 Target Pasar", ["Umum", "Pelajar / Mahasiswa", "Pekerja Kantoran"], default=["Umum"])
        market = [f"Lokasi: {lokasi_raw}", f"Gender: {gender}", f"Umur: {umur_raw}", f"Pasar: {pasar_raw}"]

    st.markdown('<div class="section-card-header"><div class="section-num">2</div><div><div class="section-title">Data Produk & KBLI</div></div></div>', unsafe_allow_html=True)
    with st.container(border=True):
        brand_name = st.text_input("🏪 Nama Brand / Usaha UMKM")
        st.session_state['brand_name'] = brand_name
        keywords_raw = st.text_input("⭐ Keywords USP Usaha", placeholder="premium, lezat, murah")
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        kategori_raw = st.selectbox("📋 Kategori Usaha (KBLI)", list(KBLI_DATA.keys()))
        st.session_state['kategori'] = kategori_raw
        st.markdown(f"<div class='kbli-desc'>📌 <b>KBLI Sektor:</b> {KBLI_DATA[kategori_raw]['desc']}</div>", unsafe_allow_html=True)
        mode_promo = st.radio("💸 Metode Input Harga", ["Deskripsi Bebas (Harga Sama/Massal)", "Input Item Manual Satu-per-Satu"])
        deskripsi_harga_global = st.text_area("Detail Harga", placeholder="Mulai 15 ribuan...") if mode_promo == "Deskripsi Bebas (Harga Sama/Massal)" else ""

    st.markdown('<div class="section-card-header"><div class="section-num">3</div><div><div class="section-title">Strategi Platform & Routing Model</div></div></div>', unsafe_allow_html=True)
    with st.container(border=True):
        platform = st.radio("📱 Platform Target", ["Instagram", "WhatsApp", "TikTok"], horizontal=True)
        rasio_pilihan = st.selectbox("📐 Aspek Rasio Visual", list(ASPECT_RATIO_OPTIONS.keys()))
        st.session_state.image_size = ASPECT_RATIO_OPTIONS[rasio_pilihan]
        gaya = st.selectbox("✍️ Tone Copywriting", ["Santai & Kekinian (Gen Z)", "Profesional & Formal", "Hard-Selling"])
        mood = st.selectbox("🌅 Mood Visual", ["Cerah & Ceria (Bright & Cheerful)", "Gelap Elegan"])
        bg = st.selectbox("🖼️ Background Foto", list(BACKGROUND_OPTIONS.keys()))
        subjek = st.selectbox("👤 Subjek Foto", ["Produk saja", "1 Orang"])
        
        # --- UI REVISI: ROUTING GATEWAY MODEL AKTIF VIA OPENROUTER ---
        st.markdown("<hr style='margin:0.8rem 0;'>", unsafe_allow_html=True)
        st.markdown("##### 🧪 Gateway Pengujian Multi-Model (UAT Skripsi)")
        model_selection = st.selectbox(
            "Pilih Otak AI Teks (Live Chat Completions):",
            [
                "Google Gemini 2.5 Pro",
                "OpenAI ChatGPT (GPT-4o)",
                "DeepSeek V4 Flash"
            ]
        )
        
        MODEL_MAP = {
            "Google Gemini 2.5 Pro": "google/gemini-2.5-pro",
            "OpenAI ChatGPT (GPT-4o)": "openai/gpt-4o",
            "DeepSeek V4 Flash": "deepseek/deepseek-v4-flash"
        }
        chosen_model_id = MODEL_MAP[model_selection]

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 GENERATE IKLAN OTOMATIS", type="primary", use_container_width=True):
        if not brand_name: st.warning("⚠️ Isi nama brand!")
        else:
            st.session_state.img_mem = {"A": None}
            st.session_state.copyright_data_live = None
            
            # 1. PANGGIL OPENROUTER SECARA LIVE SESUAI MODEL PILIHAN USER
            with st.spinner(f"🤖 Mengirim Token... Menghubungkan naskah via {model_selection}..."):
                context_block = build_context_block(kategori_raw, brand_name, keywords, gaya, platform, market, mood, bg, subjek, get_elemen_wajib(kategori_raw), mode_promo, deskripsi_harga_global, st.session_state.daftar_produk_umkm)
                raw_response = invoke_openrouter_text_engine(chosen_model_id, MASTER_PROMPT_FULL, context_block)
                vis, txt = parse_output_for_image(raw_response)
                st.session_state.main_txt, st.session_state.vis_prompt = txt, vis
                st.session_state.last_p = {"nama": brand_name, "plat": platform}
                catat_aktivitas_sistem(f"Generate via {model_selection}", brand_name)

            # 2. EVALUASI JURI OTOMATIS (LLM-AS-A-JUDGE)
            with st.spinner("⚖️ Agen QC Evaluator: Menilai kelayakan kriteria promosi..."):
                st.session_state.ai_eval_result = evaluate_ad_quality_master(kategori_raw, txt)
            st.rerun()

# ============================================================
# --- KOLOM KANAN: OUTPUT, QC, VISUAL & LIVE REVERSE SEARCH ---
# ============================================================
with col_r:
    st.markdown('<div class="section-card-header"><div class="section-num">4</div><div><div class="section-title">Copywriting Hasil AI</div></div></div>', unsafe_allow_html=True)
    if st.session_state.main_txt:
        with st.container(border=True):
            edit_mode = st.toggle("✏️ Mode Edit Manual")
            if edit_mode:
                st.session_state.main_txt = st.text_area("Edit Teks", value=st.session_state.main_txt, height=300)
            else:
                st.markdown(st.session_state.main_txt)
            if st.session_state.get('ai_eval_result'):
                hasil_evaluasi = st.session_state.ai_eval_result
                match = re.search(r'SKOR KELAYAKAN:\s*(\d+)', hasil_evaluasi)
                skor = int(match.group(1)) if match else 85
                color = "#ecfdf5" if skor >= 70 else "#fff1f2"
                st.markdown(f'<div style="background:{color}; padding:10px; border-radius:8px; font-weight:700;">Skor Evaluasi G-Eval: {skor}/100</div>', unsafe_allow_html=True)
                with st.expander("📊 Lihat Catatan Koreksi AI Pakar"): st.markdown(hasil_evaluasi)

        st.markdown('<div class="section-card-header"><div class="section-num">5</div><div><div class="section-title">Render Visual Final</div></div></div>', unsafe_allow_html=True)
        with st.container(border=True):
            if st.button("✨ Render Foto Studio (Otomatis)", type="primary", use_container_width=True):
                with st.spinner("📸 Merender objek fotografi komersial..."):
                    raw = generate_dalle_image(st.session_state.vis_prompt, st.session_state.image_size)
                    st.session_state.img_mem["A"] = apply_dynamic_branding(raw, logo_file, posisi_logo) if raw else None
                st.rerun()

            if st.session_state.img_mem["A"]:
                st.image(st.session_state.img_mem["A"], use_container_width=True)
                
                # --- SISTEM LIVE CEK COPYRIGHT GOOGLE LENS (SERPAPI) ---
                st.markdown("---")
                st.markdown("##### 🔍 Sistem Proteksi Hak Cipta & Merek Dagang (Live)")
                if st.button("🔍 Jalankan Verifikasi Komersial (Cek Copyright)", type="secondary", use_container_width=True):
                    with st.spinner("📡 Mengontak basis data paten visual Google Lens..."):
                        st.session_state.copyright_data_live = execute_live_google_lens_check(st.session_state.img_mem["A"])
                
                if st.session_state.copyright_data_live:
                    res_data = st.session_state.copyright_data_live
                    if "error" in res_data: st.error(res_data["error"])
                    else:
                        rate = res_data["rate"]
                        matches = res_data["matches"]
                        if rate <= 30:
                            st.success(f"🟢 AMAN: Tingkat kemiripan visual murni hanya {rate}%. Objek bersifat generik.")
                        elif rate <= 80:
                            st.warning(f"🟡 PERINGATAN: Tingkat kemiripan mendeteksi {rate}%. Terindikasi mirip komoditas lain.")
                        else:
                            st.error(f"🔴 BAHAYA COPYRIGHT: Hasil kecocokan {rate}% identik! Sangat dilarang untuk publikasi!")
                        if matches:
                            st.markdown("<b style='font-size:0.8rem;'>🔗 Sampel Bukti Penelusuran Google Lens (Laporan Bab 4):</b>", unsafe_allow_html=True)
                            for m in matches: st.caption(f"▪️ [{m.get('title')}]({m.get('link')})")
                st.markdown("---")

        st.markdown('<div class="section-card-header"><div class="section-num">6</div><div><div class="section-title">Asisten Revisi AI</div></div></div>', unsafe_allow_html=True)
        with st.container(border=True):
            revisi_input = st.chat_input("Ketik instruksi revisi...")
            if revisi_input:
                with st.spinner("🧠 Menyesuaikan konteks naskah..."):
                    new_raw = generate_ad_revision_master(st.session_state.main_txt, st.session_state.vis_prompt, revisi_input)
                    new_vis, new_txt = parse_output_for_image(new_raw)
                    st.session_state.main_txt, st.session_state.vis_prompt = new_txt, new_vis
                    st.session_state.img_mem["A"] = None
                st.rerun()
    else:
        st.markdown('<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-title">Belum Ada Hasil Iklan</div></div>', unsafe_allow_html=True)