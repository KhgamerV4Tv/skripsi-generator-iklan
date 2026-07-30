# Generator Konten Iklan UMKM V21 Pro

Aplikasi Streamlit untuk membantu UMKM membuat copywriting dan visual iklan berbasis Generative AI. Proyek ini dikembangkan sebagai skripsi **“Rancang Bangun Aplikasi Generator Konten Iklan UMKM Berbasis Generative Artificial Intelligence”** oleh Kevin Hartono.

Demo live: [Ad Generator V21 Pro](https://crtjlpzelkunuukw4ntet8.streamlit.app/)

## Hasil utama

- Copywriting terstruktur dengan Gemini 2.5 Pro dan master prompt berbasis konteks UMKM.
- Visual iklan menggunakan GPT Image 2 dengan target rasio feed, story, dan lanskap.
- Upload foto referensi produk, kategori KBLI, target audiens, harga/promo, tone, mood, dan background.
- LLM-as-a-Judge untuk factual consistency, kelengkapan domain, serta kesesuaian platform/tone.
- Penempatan logo dinamis dengan kontrol ukuran, opacity, dan soft shadow.
- Asisten revisi teks/visual dan unduhan hasil gambar beresolusi tinggi.
- Log penggunaan dan hasil UAT dapat disimpan ke Firestore.
- Pemeriksaan kemiripan visual opsional melalui Google Lens/SerpAPI.

Pengujian pada laporan skripsi melibatkan 10 responden UMKM dan menghasilkan nilai UAT keseluruhan **84% (Sangat Layak)**. Rincian yang dilaporkan: copywriting 90%, desain gambar 77,8%, usability 86%, akurasi teks promosi 80%, dan manfaat 86%.

## Arsitektur

```text
Streamlit UI (app15.py — entry demo live)
├── Gemini 2.5 Pro → copywriting, revisi, LLM-as-a-Judge
├── GPT Image 2 → visual iklan
├── Pillow → crop rasio, logo, opacity, shadow
├── Firestore → log penggunaan dan UAT (opsional)
└── ImgBB + Google Lens/SerpAPI → sinyal kemiripan visual (opsional)
```

`app15.py` adalah entry point yang dikonfirmasi pemilik sebagai sumber demo Streamlit live. `app.py` adalah versi refactor/modernisasi untuk pengembangan lanjutan. File bernomor lain dipertahankan sebagai riwayat iterasi penelitian kecuali pemilik proyek mengklasifikasikannya kembali.

## Menjalankan secara lokal

Persyaratan: Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
streamlit run app15.py
```

Isi `.streamlit/secrets.toml` dengan kredensial pribadi. Jangan commit file tersebut. `GEMINI_API_KEY` dan `OPENAI_API_KEY` diperlukan untuk alur utama. `ADMIN_PIN` mengaktifkan menu log admin; Firestore dan pemeriksaan Google Lens bersifat opsional.

## Pengujian

Unit test tidak memanggil layanan eksternal:

```powershell
python -m unittest discover -s tests -v
python -m compileall app15.py app.py api utils
```

Uji manual minimum:

1. Isi data brand, produk, target audiens, dan strategi platform.
2. Generate copywriting lalu periksa skor dan rincian tiga kriteria QC.
3. Render visual pada tiga target rasio.
4. Upload logo dan verifikasi posisi, ukuran, opacity, serta shadow.
5. Jalankan revisi teks dan pastikan hasil visual ditandai perlu dirender ulang.
6. Jika kredensial opsional tersedia, uji Firestore dan pemeriksaan kemiripan visual.

## Catatan privasi dan hak cipta

Fitur Google Lens mengunggah gambar ke ImgBB agar dapat diakses oleh mesin reverse image search. Aktifkan fitur hanya jika pengguna menyetujui pengiriman tersebut. Hasilnya adalah **sinyal kemiripan untuk tinjauan manual**, bukan jaminan orisinalitas, keputusan pelanggaran hak cipta, atau nasihat hukum.

## Struktur penting

```text
app15.py                       # sumber demo Streamlit live (V21 Pro)
app.py                         # versi refactor/modernisasi
master_prompt_umkm.md          # master prompt copywriting
formatter.py                   # ekspor DOCX
api/copyright_check.py         # integrasi eksternal opsional
utils/branding.py              # crop dan branding visual
utils/evaluation.py            # parsing dan klasifikasi skor QC
tests/                         # unit test tanpa network
```
