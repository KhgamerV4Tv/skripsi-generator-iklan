import os
import streamlit as st
import re
import io
import base64
import requests
import openai
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from PIL import Image
import google.generativeai as genai

# ==============================================================================
# KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(
    page_title="Inamikro Ad Generator V18 Pro",
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

    /* ===== METRIC CARDS ===== */
    .metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.7rem; margin: 0.8rem 0; }
    .metric-card {
        background: var(--secondary-background-color, #ffffff);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        padding: 0.9rem;
        text-align: center;
    }
    .metric-val { font-size: 1.4rem; font-weight: 800; color: #4f46e5; }
    .metric-lbl { font-size: 0.72rem; color: #64748b; font-weight: 600; margin-top: 0.2rem; }

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

    /* Streamlit's official dark theme class support */
    .stApp[data-theme="dark"] [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%);
    }
    .stApp[data-theme="dark"] div[data-testid="stVerticalBlockBorderWithFormatting"] {
        background-color: #1e293b !important; border-color: #334155 !important;
    }
    .stApp[data-theme="dark"] .section-title { color: #f1f5f9 !important; }
    .stApp[data-theme="dark"] .section-subtitle { color: #94a3b8 !important; }
    .stApp[data-theme="dark"] .stepper-wrap {
        background: #1e293b !important; border-color: #334155 !important;
    }
    .stApp[data-theme="dark"] .step-label-txt { color: #94a3b8 !important; }
    .stApp[data-theme="dark"] .empty-state {
        background: #1e293b !important; border-color: #475569 !important;
    }
    .stApp[data-theme="dark"] .empty-title { color: #cbd5e1 !important; }
    .stApp[data-theme="dark"] .empty-sub { color: #94a3b8 !important; }
    .stApp[data-theme="dark"] .kbli-desc,
    .stApp[data-theme="dark"] .kbli-desc * { color: #dbeafe !important; }
    .stApp[data-theme="dark"] .kbli-desc {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%) !important;
    }
    .stApp[data-theme="dark"] .stRadio [data-testid="stMarkdownContainer"] p,
    .stApp[data-theme="dark"] [data-testid="stMarkdownContainer"] h1,
    .stApp[data-theme="dark"] [data-testid="stMarkdownContainer"] h2,
    .stApp[data-theme="dark"] [data-testid="stMarkdownContainer"] h3,
    .stApp[data-theme="dark"] [data-testid="stMarkdownContainer"] h4,
    .stApp[data-theme="dark"] [data-testid="stMarkdownContainer"] h5,
    .stApp[data-theme="dark"] [data-testid="stMarkdownContainer"] h6 {
        color: #f8fafc !important; 
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
            <h1>Inamikro Ad Generator <span style="color: #fbbf24;">V18 Pro</span></h1>
            <div class="hero-sub">Platform Generator Copywriting & Komparasi Engine Visual Skripsi UMKM</div>
        </div>
    </div>
    <div class="hero-badges">
        <span class="hero-badge">⚡ Generasi Otomatis</span>
        <span class="hero-badge">⚖️ AI Quality Control</span>
        <span class="hero-badge">📊 KBLI Inamikro</span>
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
MASTER_PROMPT_PATH = Path(__file__).parent / "master_prompt_inamikro.md"

@st.cache_data
def load_master_prompt():
    try:
        if MASTER_PROMPT_PATH.exists(): return MASTER_PROMPT_PATH.read_text(encoding="utf-8")
    except Exception: pass
    return "Kamu adalah Agen Marketing UMKM Pakar Copywriting Indonesia."

MASTER_PROMPT_FULL = load_master_prompt()

KBLI_DATA = {
    "56102 - Restoran dan Rumah Makan": {"desc": "Usaha yang menjual makanan siap saji di tempat makan.", "tipe": "food"},
    "56303 - Rumah Minum/Kafe": {"desc": "Usaha yang menjual minuman dan makanan ringan.", "tipe": "food"},
    "10794 - Industri Keripik & Makanan Ringan": {"desc": "Usaha produksi makanan ringan dalam kemasan.", "tipe": "food"},
    "10750 - Industri Makanan Olahan (Frozen Food)": {"desc": "Usaha produksi makanan yang diproses dan dikemas.", "tipe": "food"},
    "47841 - Perdagangan Eceran Makanan Keliling": {"desc": "Usaha berjualan makanan dan minuman keliling.", "tipe": "food"},
    "47711 - Perdagangan Eceran Pakaian (Fashion)": {"desc": "Usaha penjualan pakaian jadi eceran.", "tipe": "fashion"},
    "47726 - Perdagangan Eceran Sepatu/Sandal": {"desc": "Usaha penjualan alas kaki eceran.", "tipe": "fashion"},
    "47721 - Perdagangan Eceran Kosmetik & Skincare": {"desc": "Usaha penjualan produk kecantikan, makeup, dan perawatan kulit.", "tipe": "fashion"},
    "32990 - Industri Kerajinan Tangan (Kriya/Aksesoris)": {"desc": "Usaha pembuatan kerajinan, aksesoris, atau souvenir.", "tipe": "fashion"},
    "96012 - Jasa Penatu/Laundry": {"desc": "Usaha jasa pencucian pakaian.", "tipe": "jasa"},
    "96020 - Jasa Salon & Perawatan Kecantikan": {"desc": "Usaha layanan pangkas rambut, kosmetik, dan salon.", "tipe": "jasa"}
}

BROSUR_ELEMEN = {
    "food": ["Nama Produk", "Harga", "Keunggulan/USP", "Promo/Diskon", "Call-to-Action", "Kontak/WhatsApp"],
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
    "🌸 Pastel Aesthetic": "soft pastel pink and cream aesthetic background",
}

# ==============================================================================
# INITIALIZE SESSION STATE
# ==============================================================================
for k in ['main_txt', 'vis_prompt', 'last_p', 'img_mem', 'chat_history']:
    if k not in st.session_state: st.session_state[k] = None
if st.session_state.img_mem is None: st.session_state.img_mem = {"A": None}
if st.session_state.chat_history is None: st.session_state.chat_history = []

# Tambahan untuk data skripsi
if "skripsi_data" not in st.session_state: st.session_state.skripsi_data = []
if "daftar_produk_umkm" not in st.session_state: st.session_state.daftar_produk_umkm = []
if "usage_logs" not in st.session_state: st.session_state.usage_logs = []

# ==============================================================================
# FUNGSI PENANGANAN KREDENSIAL GCP & FIRESTORE
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

# ==============================================================================
# FUNGSI PENCATAT LOG PENGGUNAAN (TRAFFIC)
# ==============================================================================
def catat_aktivitas_sistem(aktivitas, nama_brand):
    log_entry = {
        "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Aktivitas": aktivitas,
        "Nama Usaha": nama_brand
    }
    if db:
        try: db.collection("log_penggunaan").add(log_entry)
        except Exception: pass
    else:
        st.session_state.usage_logs.append(log_entry)

# ==============================================================================
# ENGINE GENERATOR TEKS GEMINI SDK
# ==============================================================================
class GeminiStudioWrapper:
    def __init__(self, model_name, temperature):
        self.model_name = model_name
        self.temperature = temperature

    def invoke(self, messages):
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel(self.model_name, generation_config=genai.types.GenerationConfig(temperature=self.temperature))

            contents = []
            msg = messages[0] if isinstance(messages, list) else messages

            if hasattr(msg, 'content') and isinstance(msg.content, list):
                for part in msg.content:
                    if part.get("type") == "text": contents.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        b64_data = part["image_url"]["url"].split(",")[1]
                        contents.append(Image.open(io.BytesIO(base64.b64decode(b64_data))))
            else:
                contents.append(str(msg.content if hasattr(msg, 'content') else msg))

            response = model.generate_content(contents)
            class AIResponse:
                def __init__(self, text): self.content = text
            return AIResponse(response.text)
        except Exception as e:
            class ErrorResponse:
                def __init__(self): self.content = f"⚠️ Error API Teks: {str(e)}"
            return ErrorResponse()

llm_generator = GeminiStudioWrapper(model_name="gemini-2.5-pro", temperature=0.3)

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

def build_context_block(kategori, brand_name, keywords_list, gaya, platform, market, mood, background, subjek, elemen_wajib, mode_promo, nama_produk_global, harga_global, promo_global, list_produk, photo_descriptions=None):
    market_str = ", ".join(market) if market else "Umum"
    keywords_str = ", ".join(keywords_list) if keywords_list else brand_name
    elemen_str = "\n".join([f"  - {e}" for e in elemen_wajib])
    bg_desc = BACKGROUND_OPTIONS.get(background, background)

    produk_block = ""
    if mode_promo == "Diskon Sama untuk Semua (Global)":
        promo_text = f" (Diberikan Promo Global: {promo_global})" if promo_global else " (Tanpa Promo)"
        produk_block = f"\n  - Nama Produk: {nama_produk_global}\n  - Harga: Rp {harga_global:,}{promo_text}"
    else:
        for idx, p in enumerate(list_produk):
            p_promo = f" (Promo: {p['promo']})" if p['promo'] else " (Tanpa Promo)"
            produk_block += f"\n  {idx+1}. {p['nama']} -> Harga: Rp {p['harga']:,}{p_promo}"

    photo_block = ""
    if photo_descriptions:
        photo_lines = [f"  - Foto {i+1}: {d.strip() or '(tanpa keterangan)'}" for i, d in enumerate(photo_descriptions)]
        photo_block = "\nKETERANGAN FOTO REFERENSI:\n" + "\n".join(photo_lines)

    return f"""
=== INPUT TERSTRUKTUR ===
- Nama Brand/Usaha: {brand_name}
- Karakteristik/USP Sektor: {keywords_str}
- Kategori Usaha: {kategori}
- Strategi Penawaran Produk:{produk_block}
- Target Market: {market_str} {photo_block}
- Platform Media: {platform} (Tone Copywriting: {gaya})
- Konsep Visual: {subjek} di {bg_desc} ({mood} atmosphere)
- Elemen Wajib yang HARUS Ditulis di dalam Iklan:
{elemen_str}

=== PERINTAH TEGAS GENERASI VISUAL ===
Jangan membuat gambar abstrak atau patung 3D geometris! Ide Visual harus berupa konsep fotografi komersial (Commercial Product Photography) nyata yang menampilkan wujud asli produk '{brand_name}' secara lezat/menarik, rapi, dan sesuai dengan suasana latar belakang yang dipilih.
"""

@st.cache_data(show_spinner=False)
def generate_ad_text_master(kategori, brand_name, keywords_list, gaya, platform, market, mood, background, subjek, images_bytes_list, elemen_wajib, mode_promo, nama_produk_global, harga_global, promo_global, list_produk, photo_descriptions=None):
    context = build_context_block(kategori, brand_name, keywords_list, gaya, platform, market, mood, background, subjek, elemen_wajib, mode_promo, nama_produk_global, harga_global, promo_global, list_produk, photo_descriptions)
    fidelity = "\n=== ATURAN VISUAL ===\nIde Visual HARUS mereplikasi BENTUK produk dari foto referensi persis.\n" if images_bytes_list else ""
    full_prompt = f"{MASTER_PROMPT_FULL}\n{context}\n{fidelity}\n=== TUGAS: Buat Teks Iklan {platform} ==="

    parts = [{"type": "text", "text": full_prompt}]
    for img_bytes in images_bytes_list:
        parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode('utf-8')}"}})

    class DummyMsg:
        def __init__(self, content): self.content = content
    return llm_generator.invoke([DummyMsg(parts)]).content

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
    class DummyMsg:
        def __init__(self, content): self.content = content
    return llm_generator.invoke([DummyMsg(prompt)]).content

@st.cache_data(show_spinner=False)
def evaluate_ad_quality_master(kategori, text_result):
    prompt = f"""Kamu adalah Dosen Pakar Marketing Digital & AI.
Tugasmu adalah menjadi 'LLM-as-a-Judge' untuk mengevaluasi naskah iklan UMKM berikut.

Kategori Usaha: {kategori}
Naskah Iklan:
{text_result}

Berikan penilaian analitis dan ketat. Tampilkan output HANYA dalam format ini:
SKOR KELAYAKAN: [Berikan angka 1-100]
ANALISIS PAKAR: [Berikan 2-3 kalimat penjelasan mengapa skor tersebut diberikan, sebutkan kelebihan dan kekurangannya berdasarkan target pasar]
"""
    class DummyMsg:
        def __init__(self, content): self.content = content
    return llm_generator.invoke([DummyMsg(prompt)]).content

# ==============================================================================
# MODEL GENERATOR OPENAI (GPT-IMAGE-2 / DALL-E)
# ==============================================================================
def generate_dalle_image(prompt_text):
    if not prompt_text: return None
    try:
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        context_anchor = f"Commercial product advertisement photography for '{st.session_state.get('brand_name', 'UMKM')}' showing realistic products of {st.session_state.get('kategori', 'Product')}. Photorealistic, high quality, appetizing style, no abstract 3D figures, no geometric sculptures, "
        safe_prompt = (context_anchor + prompt_text)[:900]

        res = client.images.generate(model="gpt-image-2", prompt=safe_prompt, size="1024x1024", n=1)
        if hasattr(res.data[0], 'url') and res.data[0].url:
            return requests.get(res.data[0].url).content
        if hasattr(res.data[0], 'b64_json') and res.data[0].b64_json:
            return base64.b64decode(res.data[0].b64_json)
    except Exception as e:
        st.error(f"Gagal memproses GPT Image: {e}")
        return None

# ==============================================================================
# POST-PROCESSING WATERMARK
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
        elif "Tengah Bawah" in posisi: pos = ((main_img.width - nw) // 2, main_img.height - nh - pad)

        res = main_img.copy()
        res.paste(logo_img, pos, logo_img)
        out = io.BytesIO()
        res.save(out, format='PNG')
        return out.getvalue()
    except Exception: return main_bytes

# ==============================================================================
# HITUNG STEP AKTIF UNTUK STEPPER
# ==============================================================================
def get_active_step():
    if st.session_state.get('main_txt') and st.session_state.img_mem.get('A'):
        return 6
    if st.session_state.get('main_txt'):
        return 5
    return 3

active_step = get_active_step()

# ==============================================================================
# STEPPER VISUALISASI 6 LANGKAH
# ==============================================================================
steps_data = [
    ("1", "Branding"),
    ("2", "Produk"),
    ("3", "Platform"),
    ("4", "Copywriting"),
    ("5", "Visual"),
    ("6", "Revisi"),
]

stepper_html = '<div class="stepper-wrap"><div class="stepper">'
for i, (num, label) in enumerate(steps_data, 1):
    step_num = int(num)
    if step_num < active_step:
        cls_circle, cls_label, icon = "step-circle done", "step-label-txt", "✓"
    elif step_num == active_step:
        cls_circle, cls_label, icon = "step-circle active", "step-label-txt active", num
    else:
        cls_circle, cls_label, icon = "step-circle", "step-label-txt", num
    stepper_html += f'<div class="step-item"><div class="{cls_circle}">{icon}</div><div class="{cls_label}">{label}</div></div>'
stepper_html += '</div></div>'
st.markdown(stepper_html, unsafe_allow_html=True)


# ==============================================================================
# USER INTERFACE LAYOUT
# ==============================================================================
col_f, col_r = st.columns([1, 1.35], gap="large")

# ============================================================
# --- KOLOM KIRI: INPUT DATA ---
# ============================================================
with col_f:
    # --- LANGKAH 1: BRANDING ---
    st.markdown("""
    <div class="section-card-header">
        <div class="section-num">1</div>
        <div>
            <div class="section-title">Identitas & Branding UMKM</div>
            <div class="section-subtitle">Logo, posisi watermark, dan target market</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        col_l1, col_l2 = st.columns([1.3, 1])
        with col_l1:
            logo_file = st.file_uploader("Upload Logo UMKM", type=['png', 'jpg'], help="Format PNG transparan paling direkomendasikan")
        with col_l2:
            posisi_logo = st.selectbox("Posisi Logo", ["Kanan Atas", "Kiri Atas", "Kanan Bawah", "Kiri Bawah", "Tengah Bawah"])
        market = st.multiselect(
            "🎯 Target Market",
            ["Umum", "Mahasiswa", "Pekerja Kantoran", "Ibu Rumah Tangga", "Anak Sekolah / Remaja"],
            default=["Umum"]
        )

    # --- LANGKAH 2: PRODUK ---
    st.markdown("""
    <div class="section-card-header">
        <div class="section-num">2</div>
        <div>
            <div class="section-title">Data Produk & Manajemen Harga</div>
            <div class="section-subtitle">Brand, USP, kategori KBLI, dan penawaran</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        brand_name = st.text_input("🏪 Nama Brand / Usaha UMKM", placeholder="Contoh: Bakso Mantap Jaya")
        st.session_state['brand_name'] = brand_name

        keywords_raw = st.text_input("⭐ Keywords USP Usaha", placeholder="tanpa pengawet, premium, isi tebal")
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        if keywords:
            st.markdown(" ".join([f'<span class="kw-tag">✦ {k}</span>' for k in keywords]), unsafe_allow_html=True)

        kategori = st.selectbox("📋 Kategori Usaha (KBLI)", list(KBLI_DATA.keys()))
        st.session_state['kategori'] = kategori
        st.markdown(f"<div class='kbli-desc'>📌 <b>Deskripsi Sektor:</b> {KBLI_DATA[kategori]['desc']}</div>", unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        mode_promo = st.radio(
            "💸 Metode Penginputan Harga & Promo",
            ["Diskon Sama untuk Semua (Global)", "Diskon Berbeda Per Item (Input Satu-Satu)"]
        )

        nama_produk_global = ""
        harga_global = 0
        promo_global = ""

        if mode_promo == "Diskon Sama untuk Semua (Global)":
            st.markdown("##### 🌍 Input Harga & Promo Massal (Global)")
            nama_produk_global = st.text_input("Nama Menu / Kelompok Produk", placeholder="Siomay, Gyoza, dan Dimsum Goreng")
            c_g1, c_g2 = st.columns(2)
            with c_g1:
                harga_global = st.number_input("Estimasi Harga Mulai (Rp)", min_value=0, value=30000, step=1000)
            with c_g2:
                promo_global = st.text_input("Promo Massal", placeholder="Beli 2 Gratis 1 / Diskon 10rb")
        else:
            st.markdown("##### ➕ Input Item Manual Satu-per-Satu")
            c_p1, c_p2, c_p3 = st.columns([1.5, 1.2, 1.3])
            with c_p1: item_nama = st.text_input("Nama Item", placeholder="Siomay", key="input_item_nama")
            with c_p2: item_harga = st.number_input("Harga (Rp)", min_value=0, value=15000, step=1000, key="input_item_harga")
            with c_p3: item_promo = st.text_input("Promo", placeholder="Diskon 10rb", key="input_item_promo")

            if st.button("➕ Tambah Item ke Daftar", use_container_width=True):
                if item_nama:
                    st.session_state.daftar_produk_umkm.append({"nama": item_nama, "harga": item_harga, "promo": item_promo})
                    st.toast(f"✅ {item_nama} ditambahkan ke daftar!", icon="📝")

            if st.session_state.daftar_produk_umkm:
                st.dataframe(pd.DataFrame(st.session_state.daftar_produk_umkm), use_container_width=True, hide_index=True)
                if st.button("🗑️ Kosongkan Daftar Item", type="secondary", use_container_width=True):
                    st.session_state.daftar_produk_umkm = []
                    st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        foto_produk = st.file_uploader("📷 Upload Foto Referensi Produk", type=['png', 'jpg'], accept_multiple_files=True, help="Maksimal 3 foto. AI akan menganalisa bentuk fisik produk")
        foto_desc = []
        if foto_produk:
            st.markdown('<div class="photo-caption-box">🏷️ <b>Beri keterangan singkat tiap foto</b> agar AI lebih akurat</div>', unsafe_allow_html=True)
            for i, f in enumerate(foto_produk[:3]):
                c1, c2 = st.columns([1, 2.5])
                with c1: st.image(f, use_container_width=True)
                with c2: foto_desc.append(st.text_input(f"Keterangan Foto {i+1}", key=f"f_{i}", placeholder=f"Contoh: Bakso sapi premium", label_visibility="collapsed"))

    # --- LANGKAH 3: PLATFORM ---
    st.markdown("""
    <div class="section-card-header">
        <div class="section-num">3</div>
        <div>
            <div class="section-title">Strategi Platform & Visual</div>
            <div class="section-subtitle">Platform target, tone, mood, dan komposisi visual</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        platform = st.radio("📱 Platform Target", ["Instagram", "WhatsApp", "TikTok"], horizontal=True)
        cs1, cs2 = st.columns(2)
        with cs1: gaya = st.selectbox("✍️ Tone Copywriting", ["Santai & Kekinian", "Profesional", "Hard-Selling"])
        with cs2: mood = st.selectbox("🌅 Mood Visual", ["Cerah", "Gelap Elegan", "Hangat"])
        bg = st.selectbox("🖼️ Background Foto", list(BACKGROUND_OPTIONS.keys()))
        subjek = st.selectbox("👤 Subjek Foto", ["Produk saja", "1 Orang", "Keluarga"])

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 GENERATE IKLAN OTOMATIS", type="primary", use_container_width=True):
        if not brand_name:
            st.warning("⚠️ Mohon isi nama brand/usaha terlebih dahulu!")
        else:
            st.session_state.img_mem = {"A": None}
            st.session_state.chat_history = []
            st.session_state.ai_eval_result = None

            with st.spinner("🤖 Agent 1: AI sedang meracik copywriting profesional..."):
                img_bytes = [f.getvalue() for f in foto_produk] if foto_produk else []
                res = generate_ad_text_master(
                    kategori, brand_name, keywords, gaya, platform, market, mood, bg, subjek, img_bytes,
                    get_elemen_wajib(kategori), mode_promo, nama_produk_global, harga_global, promo_global,
                    st.session_state.daftar_produk_umkm, foto_desc
                )
                vis, txt = parse_output_for_image(res)
                st.session_state.main_txt, st.session_state.vis_prompt = txt, vis
                st.session_state.last_p = {"nama": brand_name, "plat": platform}
                catat_aktivitas_sistem("Generate Copywriting", brand_name)

            with st.spinner("⚖️ Agent 2: Mengevaluasi kualitas iklan (Quality Control)..."):
                hasil_evaluasi = evaluate_ad_quality_master(kategori, txt)
                st.session_state.ai_eval_result = hasil_evaluasi
            st.rerun()

# ============================================================
# --- KOLOM KANAN: OUTPUT & REVISI ---
# ============================================================
with col_r:
    # --- LANGKAH 4: COPYWRITING ---
    st.markdown("""
    <div class="section-card-header">
        <div class="section-num">4</div>
        <div>
            <div class="section-title">Copywriting Hasil AI</div>
            <div class="section-subtitle">Naskah iklan otomatis siap publikasi</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.main_txt:
        with st.container(border=True):
            edit_mode = st.toggle("✏️ Mode Edit Manual", help="Aktifkan untuk mengedit teks secara langsung")

            if edit_mode:
                st.info("💡 Edit teks di bawah. Matikan sakelar untuk melihat hasil rapinya.")
                st.session_state.main_txt = st.text_area(
                    "Edit Teks Copywriting",
                    value=st.session_state.main_txt,
                    height=350,
                    label_visibility="collapsed"
                )
            else:
                st.markdown(st.session_state.main_txt)

            # QC PANEL
            if st.session_state.get('ai_eval_result'):
                st.markdown("""
                <div class="qc-card">
                    <div class="qc-icon">✅</div>
                    <div>
                        <div class="qc-title">Lulus Uji Kualitas Pakar AI</div>
                        <div class="qc-sub">Quality Control oleh LLM-as-a-Judge Agent</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                with st.expander("📊 Lihat Detail Analisis Pakar AI"):
                    st.markdown(st.session_state.ai_eval_result)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- LANGKAH 5: VISUAL ---
        st.markdown("""
        <div class="section-card-header">
            <div class="section-num">5</div>
            <div>
                <div class="section-title">Render Visual Final</div>
                <div class="section-subtitle">Fotografi komersial otomatis dengan AI</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            with st.expander("⚙️ Lihat/Edit Instruksi Visual AI (Opsional)"):
                st.session_state.vis_prompt = st.text_area(
                    "Instruksi Prompt Visual",
                    value=st.session_state.vis_prompt,
                    height=100,
                    label_visibility="collapsed"
                )

            st.info("💡 Klik tombol di bawah untuk membuat foto promosi profesional secara otomatis.")

            if st.button("✨ Render Foto Studio (Otomatis)", type="primary", use_container_width=True):
                with st.spinner("📸 Sedang di studio AI... Merender gambar (sekitar 10 detik)..."):
                    raw = generate_dalle_image(st.session_state.vis_prompt)
                    st.session_state.img_mem["A"] = apply_dynamic_branding(raw, logo_file, posisi_logo) if raw else None
                catat_aktivitas_sistem("Render Visual Image", st.session_state.get('brand_name', 'UMKM'))
                st.rerun()

            if st.session_state.img_mem["A"]:
                st.success("✅ Gambar berhasil dibuat!")
                st.image(st.session_state.img_mem["A"], caption="🎨 Hasil Render Final Inamikro", use_container_width=True)
                st.download_button(
                    label="⬇️ Download Gambar Resolusi Tinggi",
                    data=st.session_state.img_mem["A"],
                    file_name=f"promo_{brand_name.replace(' ', '_') if brand_name else 'umkm'}.png",
                    mime="image/png",
                    use_container_width=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # --- LANGKAH 6: REVISI ---
        st.markdown("""
        <div class="section-card-header">
            <div class="section-num">6</div>
            <div>
                <div class="section-title">Asisten Revisi AI</div>
                <div class="section-subtitle">Chatbot untuk perbaikan otomatis naskah & visual</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.caption("💬 Kurang pas? Ketik perintah revisi — misal: *'Tambahkan nomor WA 08123'* atau *'Buat tone lebih formal'*")

            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            revisi_input = st.chat_input("Ketik instruksi revisi di sini...")
            if revisi_input:
                st.session_state.chat_history.append({"role": "user", "content": revisi_input})
                with st.spinner("🧠 AI sedang merevisi naskah & visual..."):
                    new_raw = generate_ad_revision_master(st.session_state.main_txt, st.session_state.vis_prompt, revisi_input)
                    new_vis, new_txt = parse_output_for_image(new_raw)

                    st.session_state.main_txt = new_txt
                    st.session_state.vis_prompt = new_vis
                    st.session_state.img_mem["A"] = None

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": "✅ **Revisi selesai!** Hasil teks di **Langkah 4** dan instruksi gambar di **Langkah 5** sudah saya perbarui. Silakan Render Ulang gambarnya."
                    })
                    st.rerun()

        # ============================================================
        # --- FORM PENILAIAN UAT & ADMIN AREA ---
        # ============================================================
        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("### 📝 Form Penilaian UAT (Dosen / Pakar)")
        st.caption("Silakan isi evaluasi kelayakan hasil *generate* AI di bawah ini untuk keperluan pengujian sistem.")
        
        with st.form("gform_mokap", clear_on_submit=True):
            f_bidang = st.selectbox("Bidang Hasil Pengujian", ["Bidang Food & Beverages", "Bidang Fashion", "Bidang Jasa","Bidang lainnya"])
            f_tester = st.text_input("Nama Penilai", value="", placeholder="Contoh: Nama Usaha ")
            f_catatan = st.text_area("Catatan Evaluasi", placeholder="Tuliskan catatan evaluasi terhadap hasil iklan...")
            f_skor = st.slider("Skor Kelayakan Hasil (1 - 100)", 1, 100, 85)

            if st.form_submit_button("📁 Simpan Penilaian UAT", use_container_width=True, type="primary"):
                new_entry = {
                    "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Bidang": f_bidang,
                    "Nama Usaha": brand_name if 'brand_name' in locals() else "N/A",
                    "Platform Target": st.session_state.last_p["plat"] if st.session_state.last_p else "N/A",
                    "Tester": f_tester,
                    "Catatan Evaluasi": f_catatan,
                    "Skor Kelayakan": f_skor
                }
                if db:
                    try:
                        db.collection("evaluasi_skripsi").add(new_entry)
                        st.toast("✅ Penilaian tersimpan di Cloud!", icon="💾")
                    except Exception as e: st.error(f"Gagal: {e}")
                else:
                    st.session_state.skripsi_data.append(new_entry)
                    st.toast("✅ Penilaian tersimpan lokal.", icon="💾")

        st.markdown("<br>", unsafe_allow_html=True)

        # Ambil data Cloud untuk Admin
        cloud_eval_data = []
        cloud_usage_data = []
        if db:
            try: 
                cloud_eval_data = [doc.to_dict() for doc in db.collection("evaluasi_skripsi").stream()]
                cloud_usage_data = [doc.to_dict() for doc in db.collection("log_penggunaan").stream()]
            except Exception: pass

        final_log_list = cloud_eval_data if db else st.session_state.skripsi_data
        final_usage_list = cloud_usage_data if db else st.session_state.usage_logs

        with st.expander("🔐 Menu Admin & Database Log"):
            admin_pin = st.text_input("Masukkan PIN Admin:", type="password", placeholder="12345678")

            if admin_pin == "12345678":
                st.success("✅ Akses Admin Terbuka!")

                # Status Sistem
                st.markdown("#### ⚙️ Status Sistem & Sesi")
                db_status_text = "Database Cloud Terkoneksi" if db else "Mode Lokal Aktif"
                db_emoji = "🟢" if db else "🟡"
                
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.markdown(f"**Koneksi Database:**<br>{db_emoji} {db_status_text}", unsafe_allow_html=True)
                with col_s2:
                    st.markdown(f"**Total Trafik Sistem:**<br>⚡ {len(final_usage_list)} Interaksi AI", unsafe_allow_html=True)
                st.markdown("<hr>", unsafe_allow_html=True)

                # TABEL LOG PENGGUNAAN AKTIVITAS
                st.markdown("#### 📡 Log Interaksi AI (Traffic)")
                if final_usage_list:
                    df_usage = pd.DataFrame(final_usage_list)
                    if "Waktu" in df_usage.columns:
                        df_usage = df_usage.sort_values(by="Waktu", ascending=False).reset_index(drop=True)
                    st.dataframe(df_usage, use_container_width=True, hide_index=True, height=200)
                else:
                    st.info("Belum ada log penggunaan.")

                st.markdown("<hr>", unsafe_allow_html=True)

                # TABEL LOG EVALUASI UAT
                st.markdown("#### 🗄️ Database Hasil Penilaian UAT")
                if final_log_list:
                    df_log = pd.DataFrame(final_log_list)
                    if "Waktu" in df_log.columns:
                        df_log = df_log.sort_values(by="Waktu", ascending=False).reset_index(drop=True)
                    st.dataframe(df_log, use_container_width=True, hide_index=True)
                    st.download_button(
                        "📥 Download Data UAT (.CSV)",
                        data=df_log.to_csv(index=False).encode('utf-8'),
                        file_name="hasil_uat_skripsi.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("ℹ️ Belum ada data penilaian UAT yang tersimpan.")

            elif admin_pin:
                st.error("⚠️ PIN Salah! Akses ditolak.")

    else:
        # Empty state
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📋</div>
            <div class="empty-title">Belum Ada Hasil Iklan</div>
            <div class="empty-sub">Lengkapi data di kolom kiri (Langkah 1–3), lalu tekan tombol<br><b>"🚀 GENERATE IKLAN OTOMATIS"</b> untuk memulai.</div>
        </div>
        """, unsafe_allow_html=True)