# =====================================================================
# config.py
# Fungsi : pusat konfigurasi (lokasi file sumber + alamat koneksi database).
# Dipakai oleh : extract.py (CSV_PATH, XLSX_PATH, SOURCE_URL) dan load.py (TARGET_URL).
# Alasan dipisah: nilai yang bisa berubah (password, host, nama database)
#                 tidak ditulis di dalam logika ETL dan tidak ikut ke Git.
# =====================================================================
import os                                   # untuk membaca environment variable (os.getenv)
from pathlib import Path                    # untuk menyusun path file yang aman di Windows/Linux
from urllib.parse import quote_plus         # meng-encode karakter khusus pada password agar URL valid

from dotenv import load_dotenv              # membaca file .env dan memasukkannya ke environment variable

# ---------------------------------------------------------------------
# 1. MEMBACA FILE .env
# ---------------------------------------------------------------------
# Membaca konfigurasi dari file .env di folder utama project
ROOT_DIR = Path(__file__).resolve().parent.parent   # folder induk dari folder etl/ (root project)
load_dotenv(ROOT_DIR / ".env")                      # muat isi .env; nilai rahasia tidak ditulis di kode

# ---------------------------------------------------------------------
# 2. LOKASI FILE SUMBER
# ---------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data" # folder etl/data tempat file sumber disimpan
CSV_PATH = DATA_DIR / "penjualan.csv"               # sumber 1: data transaksi penjualan (CSV)
XLSX_PATH = DATA_DIR / "produk.xlsx"                # sumber 2: master produk (Excel)

# ---------------------------------------------------------------------
# 3. PARAMETER KONEKSI DATABASE (diambil dari .env)
# ---------------------------------------------------------------------
DB_USER = os.getenv("DB_USER", "")                                  # user PostgreSQL (kosong jika belum diisi)
DB_PASSWORD_SOURCE = quote_plus(os.getenv("DB_PASSWORD_SOURCE", ""))  # password DB sumber; karakter seperti @ dan : di-encode
DB_PASSWORD_TARGET = quote_plus(os.getenv("DB_PASSWORD_TARGET", ""))  # password DB tujuan (data warehouse)
DB_HOST = os.getenv("DB_HOST", "localhost")                         # alamat server; default localhost
SOURCE_PORT = os.getenv("SOURCE_PORT", "5432")                      # port DB sumber; default PostgreSQL 5432
TARGET_PORT = os.getenv("TARGET_PORT", "5432")                      # port DB tujuan
SOURCE_DB = os.getenv("SOURCE_DB", "")                              # nama database sumber (berisi tabel pelanggan)
TARGET_DB = os.getenv("TARGET_DB", "")                              # nama database tujuan (data warehouse)

# ---------------------------------------------------------------------
# 4. MEMBENTUK URL KONEKSI SQLALCHEMY
# ---------------------------------------------------------------------
def buat_url(user, password, host, port, database):
    # Validasi awal: user dan nama database wajib ada, jika tidak koneksi pasti gagal
    if not all([user, database]):
        raise ValueError("Konfigurasi DB_USER dan nama database belum diisi di file .env.")
    # Format URL: dialek+driver://user:password@host:port/namadatabase
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

# URL dibuat sekali saat modul diimpor, lalu dipakai oleh extract.py dan load.py
SOURCE_URL = buat_url(DB_USER, DB_PASSWORD_SOURCE, DB_HOST, SOURCE_PORT, SOURCE_DB)  # koneksi ke database sumber
TARGET_URL = buat_url(DB_USER, DB_PASSWORD_TARGET, DB_HOST, TARGET_PORT, TARGET_DB)  # koneksi ke data warehouse
