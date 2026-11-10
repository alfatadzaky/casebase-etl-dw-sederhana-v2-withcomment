# =====================================================================
# extract.py
# Fungsi : tahap EXTRACT. Membaca tiga sumber data berformat berbeda
#          (CSV, Excel, tabel PostgreSQL) menjadi tiga DataFrame mentah.
# Prinsip: data dibaca apa adanya. Pembersihan TIDAK dilakukan di sini,
#          tetapi di tahap Transform agar setiap perubahan bisa dicatat.
# =====================================================================
import logging                                  # untuk mencatat jumlah baris yang dibaca

import pandas as pd                             # membaca CSV, Excel, dan hasil query SQL ke DataFrame
from sqlalchemy import create_engine            # membuat koneksi ke database sumber

from config import CSV_PATH, XLSX_PATH, SOURCE_URL   # lokasi file dan alamat database dari config.py

log = logging.getLogger(__name__)               # logger khusus modul ini

# ---------------------------------------------------------------------
# 1. EXTRACT
# ---------------------------------------------------------------------
def extract():
    log.info("=== EXTRACT ===")                 # penanda awal tahap Extract pada log

    # 1a. Extract CSV (penjualan)
    df_jual = pd.read_csv(
        CSV_PATH,                               # lokasi file penjualan.csv
        sep=";",                                # pemisah kolom pada file ini adalah titik koma
        dtype=str,                              # semua kolom dibaca sebagai teks agar "007" atau "Rp 15.000" tidak berubah
        encoding="utf-8-sig"                    # utf-8-sig membuang karakter BOM di awal file (umum dari Excel)
    )
    log.info("penjualan.csv : %d baris, %d kolom", *df_jual.shape)   # shape = (baris, kolom), di-unpack ke %d %d

    # 1b. Extract Excel (produk)
    df_produk = pd.read_excel(
        XLSX_PATH,                              # lokasi file produk.xlsx
        sheet_name="Produk",                    # hanya sheet bernama "Produk" yang dibaca
        dtype=str                               # semua kolom dibaca sebagai teks, sama alasannya dengan CSV
    )
    log.info("produk.xlsx   : %d baris, %d kolom", *df_produk.shape)

    # 1c. Extract database (pelanggan)
    src = create_engine(SOURCE_URL)             # membuat koneksi ke database sumber
    try:
        df_pel = pd.read_sql("SELECT * FROM pelanggan", src)   # ambil seluruh kolom dan baris tabel pelanggan
        df_pel = df_pel.astype(object)          # ubah ke tipe object agar nilai kosong/tipe campuran tetap seperti aslinya
    finally:
        src.dispose()                           # koneksi selalu ditutup, baik berhasil maupun error
    log.info("db.pelanggan  : %d baris, %d kolom", *df_pel.shape)

    return df_jual, df_produk, df_pel           # tiga DataFrame mentah diteruskan ke tahap Transform

# ---------------------------------------------------------------------
# 2. MENJALANKAN DAN MENGECEK HASIL EXTRACT
# ---------------------------------------------------------------------
# Blok ini hanya jalan jika file dijalankan langsung (python extract.py),
# bukan saat diimpor oleh main.py. Berguna untuk menguji Extract secara terpisah.
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,                                     # tampilkan log level INFO ke atas
        format="%(asctime)s [%(levelname)s] %(message)s"        # format: waktu [level] pesan
    )

    df_jual, df_produk, df_pel = extract()      # jalankan extract dan tampung tiga hasilnya

    print("\n=== DATA PENJUALAN ===")
    print(df_jual.head())                       # lima baris pertama penjualan

    print("\n=== DATA PRODUK ===")
    print(df_produk.head())                     # lima baris pertama produk

    print("\n=== DATA PELANGGAN ===")
    print(df_pel.head())                        # lima baris pertama pelanggan

    print("\n=== INFORMASI DATA ===")

    print("\nData Penjualan:")
    df_jual.info()                              # ringkasan kolom, tipe data, dan jumlah nilai non-kosong

    print("\nData Produk:")
    df_produk.info()

    print("\nData Pelanggan:")
    df_pel.info()
