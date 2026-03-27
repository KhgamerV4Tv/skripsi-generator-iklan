import streamlit as st
import google.generativeai as genai
import time
import os
from dotenv import load_dotenv

# ==============================================================================
# KONFIGURASI API KEY (AMAN DARI GITHUB)
# ==============================================================================
# Load variabel dari file .env
load_dotenv()

# Ambil API key dari file .env
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro') 
    API_SUCCESS = True
except:
    API_SUCCESS = False