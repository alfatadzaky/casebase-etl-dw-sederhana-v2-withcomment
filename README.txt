CASEBASE ETL-DW - VERSI KODE SEDERHANA

Struktur:
- etl/extract.py: mengambil data CSV, Excel, dan tabel pelanggan dari PostgreSQL.
- etl/transform/dim_*.py: satu file untuk setiap dimensi.
- etl/transform/fakta_penjualan.py: membentuk tabel fakta.
- etl/load.py: memuat seluruh tabel ke PostgreSQL DW.
- etl/main.py: mengatur urutan proses ETL.

PERSIAPAN:
1. Pastikan file penjualan.csv dan produk.xlsx berada di etl/data/.
2. Pastikan database sumber memiliki tabel pelanggan.
3. Salin .env.example menjadi .env di folder utama project.
4. Isi konfigurasi database pada .env.
5. Buat virtual environment dan install requirements.

MENJALANKAN:
Dari folder utama project:
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python -m etl.main

CATATAN:
- Load menggunakan full refresh: tabel DW lama dihapus lalu dibuat ulang.
- Baris key 0 pada dimensi digunakan untuk data yang tidak diketahui/tidak cocok.
- Fakta menggunakan primary key komposit (id_transaksi, produk_key).
- Jika satu transaksi memiliki produk yang sama pada lebih dari satu baris,
  proses akan berhenti dan memberi pesan agar grain/primary key diperiksa.
- Kode ini belum diuji koneksi ke database kalian. Pastikan .env dan PostgreSQL
  sesuai sebelum menjalankan.
- Transaksi dengan qty <= 0 tidak dibuang, tetapi disimpan di tabel reject_fakta_penjualan
  (data asli apa adanya + alasan). Tabel ini dibuat ulang pada setiap proses
  (full refresh) dan tidak memiliki PK/FK. Duplikat identik tetap dibuang.
