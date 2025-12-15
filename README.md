````markdown
# 🏠 Prediksi Harga Rumah (End-to-End MLOps)

Proyek ini adalah implementasi sistem prediksi harga rumah menggunakan Machine Learning yang di-deploy menggunakan **Docker**. Proyek ini terdiri dari dua komponen utama:
1.  **Backend API:** Server yang memproses data dan memberikan prediksi harga.
2.  **Frontend:** Antarmuka pengguna berbasis Web (Streamlit) untuk kemudahan penggunaan.

---

## 📋 Prasyarat

Sebelum memulai, pastikan komputer Anda telah terinstal:
* [Git](https://git-scm.com/)
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Pastikan statusnya *Running*)

---

## 🚀 Panduan Instalasi (Dari Awal Sampai Akhir)

Ikuti langkah-langkah berikut untuk menjalankan aplikasi ini di komputer lokal Anda.

### 1. Clone Repositori
Buka Terminal (Mac/Linux) atau Command Prompt/PowerShell (Windows) dan jalankan perintah berikut untuk mengunduh proyek:

```bash
# Clone repository ke folder bernama 'ML_Project_Rumah'
git clone [https://github.com/barunaxyz/PrediksiHargaRumah.git](https://github.com/barunaxyz/PrediksiHargaRumah.git) ML_Project_Rumah
````

### 2\. Masuk ke Direktori Proyek

Pindah ke dalam folder yang baru saja dibuat:

```bash
cd ML_Project_Rumah
```

### 3\. Jalankan Aplikasi dengan Docker Compose

Kita tidak perlu menginstal Python atau library secara manual. Docker akan menyiapkan semuanya untuk Anda. Jalankan perintah ini:

```bash
docker compose up -d
```

  * `up`: Membangun dan menjalankan container.
  * `-d`: Menjalankan di latar belakang (detached mode) agar terminal tidak terkunci.

### 4\. Verifikasi Instalasi

Pastikan kedua layanan (`house_price_api` dan `house_price_frontend`) berjalan dengan baik:

```bash
docker compose ps
```

*Pastikan status pada kolom `STATUS` adalah **Up**.*

-----

## 💻 Cara Menggunakan Aplikasi

Setelah langkah di atas berhasil, Anda dapat mengakses aplikasi melalui browser.

### 🎨 1. Akses Frontend (Antarmuka Pengguna)

Gunakan ini untuk mencoba prediksi secara visual.

  * **URL:** [http://localhost:8501](https://www.google.com/search?q=http://localhost:8501)
  * **Cara Pakai:** Masukkan data fitur rumah (luas, jumlah kamar, lokasi, dll) pada form yang tersedia, lalu klik tombol "Prediksi".

### ⚙️ 2. Akses Backend (API Endpoint)

Gunakan ini jika Anda ingin mengintegrasikan model dengan aplikasi lain atau melakukan testing via Postman/cURL.

  * **Base URL:** [http://localhost:5000](https://www.google.com/search?q=http://localhost:5000)
  * **Contoh Request (cURL):**

<!-- end list -->

```bash
curl -X POST http://localhost:5000/predict \
     -H "Content-Type: application/json" \
     -d '{"luas_tanah": 100, "kamar_tidur": 3, "kamar_mandi": 2}'
```

-----

## 🛠️ Manajemen Container

### Melihat Log (Debugging)

Jika terjadi error atau Anda ingin melihat apa yang terjadi di belakang layar:

```bash
# Melihat log backend
docker compose logs -f house_price_api

# Melihat log frontend
docker compose logs -f house_price_frontend
```

### Mematikan Aplikasi

Jika Anda sudah selesai menggunakan aplikasi, matikan container untuk menghemat resource komputer:

```bash
docker compose down
```

-----

## 📂 Struktur Proyek

```
ML_Project_Rumah/
├── docker-compose.yml   # Konfigurasi orkestrasi container
├── app.py               # Kode utama (entry point)
├── requirements.txt     # Daftar pustaka Python
├── model/               # Folder penyimpanan model ML (.pkl)
└── Dockerfile           # Konfigurasi image Docker
```

```
```
