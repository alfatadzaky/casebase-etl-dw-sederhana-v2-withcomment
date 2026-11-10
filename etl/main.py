# =====================================================================
# main.py
# Fungsi : perangkai (orkestrator) pipeline. Memanggil Extract, lalu
#          Transform tiap tabel, lalu Load, sesuai urutan ketergantungan data.
# Jalankan dari folder etl/ dengan: python main.py
# =====================================================================
import logging                                  # pencatatan proses ke terminal
import sys                                      # dipakai untuk mengarahkan log ke stdout

from extract import extract                     # fungsi tahap Extract

from transform.dim_produk import transform_dim_produk            # transform dimensi produk
from transform.dim_pelanggan import build_dim_pelanggan          # transform dimensi pelanggan
from transform.dim_waktu import build_dim_waktu                  # transform dimensi waktu
from transform.dim_metode_bayar import build_dim_metode_bayar    # transform dimensi metode bayar
from transform.fakta_penjualan import transform_fakta_penjualan  # transform fakta + reject

from load import load                           # fungsi tahap Load

# ---------------------------------------------------------------------
# 1. KONFIGURASI LOGGING
# ---------------------------------------------------------------------
# stream=sys.stdout agar urutan log dan tabel (print) tidak tertukar di terminal
logging.basicConfig(
    level=logging.INFO,                                     # tampilkan log level INFO ke atas
    format="%(asctime)s [%(levelname)s] %(message)s",       # format: waktu [level] pesan
    stream=sys.stdout,                                      # log dan print memakai saluran yang sama
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# 2. FUNGSI BANTU TAMPILAN
# ---------------------------------------------------------------------
def judul(teks):
    """Cetak satu baris kosong lalu judul bagian, supaya output tidak mepet."""
    print()                                     # baris kosong pemisah
    log.info("=== %s ===", teks)                 # judul bagian pada log

def tampilkan(df):
    """Cetak 5 baris pertama dan jumlah baris sebuah tabel."""
    print(df.head().to_string(index=False))     # pratinjau 5 baris tanpa nomor indeks
    print(f"Jumlah baris: {len(df)}")            # jumlah total baris tabel

# ---------------------------------------------------------------------
# 3. ALUR UTAMA ETL
# ---------------------------------------------------------------------
def main():
    log.info("===== MEMULAI ETL TOKOMAJU =====")

    # EXTRACT (judul "=== EXTRACT ===" dicetak di dalam extract())
    print()
    df_penjualan, df_produk, df_pelanggan = extract()   # tiga DataFrame mentah dari CSV, Excel, dan database

    # TRANSFORM
    judul("TRANSFORM")

    # Keempat dimensi dibentuk lebih dulu karena fakta membutuhkan surrogate key dari dimensi
    judul("DIMENSI PRODUK")
    dim_produk = transform_dim_produk(df_produk)                # dari master produk (Excel)
    tampilkan(dim_produk)

    judul("DIMENSI PELANGGAN")
    dim_pelanggan = build_dim_pelanggan(df_pelanggan)           # dari master pelanggan (database)
    tampilkan(dim_pelanggan)

    judul("DIMENSI WAKTU")
    dim_waktu = build_dim_waktu(df_penjualan)                   # dari tanggal unik pada transaksi
    tampilkan(dim_waktu)

    judul("DIMENSI METODE BAYAR")
    dim_metode_bayar = build_dim_metode_bayar(df_penjualan)     # dari metode bayar unik pada transaksi
    tampilkan(dim_metode_bayar)

    # Fakta dibentuk terakhir karena memerlukan keempat dimensi di atas
    judul("FAKTA PENJUALAN")
    fakta_penjualan, reject_fakta = transform_fakta_penjualan(  # menghasilkan dua tabel sekaligus
        df_penjualan,
        dim_pelanggan,
        dim_produk,
        dim_waktu,
        dim_metode_bayar
    )
    tampilkan(fakta_penjualan)

    judul("REJECT FAKTA PENJUALAN")
    tampilkan(reject_fakta)
    print("Ringkasan alasan ditolak:")
    print(reject_fakta["alasan_ditolak"].value_counts().to_string())   # jumlah baris per alasan penolakan

    # LOAD
    judul("LOAD")
    load(                                       # memuat enam tabel dalam satu transaksi
        dim_produk,
        dim_pelanggan,
        dim_waktu,
        dim_metode_bayar,
        fakta_penjualan,
        reject_fakta
    )

    print()
    log.info("===== ETL TOKOMAJU SELESAI =====")

# Titik masuk program: main() hanya dijalankan jika file ini dieksekusi langsung
if __name__ == "__main__":
    main()
