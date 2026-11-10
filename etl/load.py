# =====================================================================
# load.py
# Fungsi : tahap LOAD. Memuat enam tabel (4 dimensi, 1 fakta, 1 reject)
#          ke PostgreSQL, memvalidasi jumlah baris, lalu membuat PK dan FK.
# Prinsip: seluruh proses berada dalam SATU transaksi (atomik). Jika ada
#          satu langkah gagal, semua perubahan dibatalkan (rollback).
# =====================================================================
import logging                                  # untuk mencatat jumlah baris yang berhasil dimuat
from sqlalchemy import create_engine, text      # create_engine = koneksi; text = membungkus perintah SQL mentah

from config import TARGET_URL                   # alamat database tujuan (data warehouse)

log = logging.getLogger(__name__)

def load(dim_produk, dim_pelanggan, dim_waktu, dim_metode_bayar,
         fakta_penjualan, reject_fakta):
    """Memuat ulang seluruh tabel DW (termasuk tabel reject) dan membuat primary/foreign key."""
    engine = create_engine(TARGET_URL)          # koneksi ke data warehouse

    try:
        # engine.begin() membuka satu transaksi: commit otomatis jika blok selesai
        # tanpa error, rollback otomatis jika ada exception di dalamnya.
        with engine.begin() as conn:
            # -------------------------------------------------------------
            # 1. HAPUS TABEL LAMA (full refresh)
            # -------------------------------------------------------------
            # PERINGATAN: perintah DROP di bawah MENGHAPUS PERMANEN tabel hasil ETL
            # sebelumnya beserta isinya. Aman dijalankan ulang karena seluruh tabel
            # dibuat lagi pada langkah 2. Karena berada dalam transaksi, jika proses
            # gagal di tengah jalan, penghapusan ini ikut dibatalkan dan data lama utuh.
            # Hapus tabel lama dari fakta ke dimensi agar tidak melanggar FK
            # (tabel yang bergantung dihapus lebih dulu: reject dan fakta, baru dimensi)
            conn.execute(text("DROP TABLE IF EXISTS reject_fakta_penjualan"))
            conn.execute(text("DROP TABLE IF EXISTS fakta_penjualan"))
            conn.execute(text("DROP TABLE IF EXISTS dim_metode_bayar"))
            conn.execute(text("DROP TABLE IF EXISTS dim_waktu"))
            conn.execute(text("DROP TABLE IF EXISTS dim_produk"))
            conn.execute(text("DROP TABLE IF EXISTS dim_pelanggan"))

            # -------------------------------------------------------------
            # 2. MEMUAT TABEL + VALIDASI JUMLAH BARIS
            # -------------------------------------------------------------
            # Urutan: dimensi dulu, baru fakta dan reject. Tuple = (nama tabel, DataFrame)
            # Buat tabel dan isi data
            for nama, df in [
                ("dim_pelanggan", dim_pelanggan),
                ("dim_produk", dim_produk),
                ("dim_waktu", dim_waktu),
                ("dim_metode_bayar", dim_metode_bayar),
                ("fakta_penjualan", fakta_penjualan),
                ("reject_fakta_penjualan", reject_fakta),
            ]:
                # to_sql membuat tabel baru dan mengisinya; tipe kolom ditebak pandas,
                # dan belum ada primary key / foreign key pada tahap ini
                df.to_sql(nama, conn, if_exists="replace", index=False)
                # hitung jumlah baris yang benar-benar tersimpan di PostgreSQL
                jumlah = conn.execute(
                    text(f'SELECT COUNT(*) FROM "{nama}"')
                ).scalar_one()
                # validasi: jumlah di database harus sama dengan jumlah baris DataFrame
                if jumlah != len(df):
                    raise ValueError(f"Jumlah data tabel {nama} tidak sesuai.")   # memicu rollback seluruh transaksi
                log.info("%s berhasil dimuat: %d baris", nama, jumlah)

            # -------------------------------------------------------------
            # 3. PRIMARY KEY DIMENSI
            # -------------------------------------------------------------
            # Surrogate key tiap dimensi dijadikan primary key (unik dan tidak kosong)
            conn.execute(text("ALTER TABLE dim_pelanggan ADD PRIMARY KEY (pelanggan_key)"))
            conn.execute(text("ALTER TABLE dim_produk ADD PRIMARY KEY (produk_key)"))
            conn.execute(text("ALTER TABLE dim_waktu ADD PRIMARY KEY (waktu_key)"))
            conn.execute(text("ALTER TABLE dim_metode_bayar ADD PRIMARY KEY (metode_bayar_key)"))

            # -------------------------------------------------------------
            # 4. PRIMARY KEY FAKTA DAN FOREIGN KEY KE DIMENSI
            # -------------------------------------------------------------
            # Primary key fakta dan relasi ke dimensi
            # PK komposit (id_transaksi, produk_key): satu transaksi bisa memuat beberapa produk
            conn.execute(text(
                "ALTER TABLE fakta_penjualan "
                "ADD PRIMARY KEY (id_transaksi, produk_key)"
            ))
            # Empat FK sekaligus: setiap key pada fakta harus ada di tabel dimensinya.
            # Inilah yang membentuk relasi star schema (fakta di tengah, dimensi di sekelilingnya).
            conn.execute(text("""
                ALTER TABLE fakta_penjualan
                ADD CONSTRAINT fk_fakta_pelanggan
                    FOREIGN KEY (pelanggan_key) REFERENCES dim_pelanggan(pelanggan_key),
                ADD CONSTRAINT fk_fakta_produk
                    FOREIGN KEY (produk_key) REFERENCES dim_produk(produk_key),
                ADD CONSTRAINT fk_fakta_waktu
                    FOREIGN KEY (waktu_key) REFERENCES dim_waktu(waktu_key),
                ADD CONSTRAINT fk_fakta_metode_bayar
                    FOREIGN KEY (metode_bayar_key) REFERENCES dim_metode_bayar(metode_bayar_key)
            """))
            # Tabel reject sengaja tidak diberi PK/FK: hanya arsip penelusuran, bukan bagian star schema

        # Baris ini baru tercapai setelah blok "with" selesai, artinya transaksi sudah COMMIT
        log.info("Seluruh data berhasil dimuat ke Data Warehouse.")
    finally:
        engine.dispose()                        # koneksi selalu ditutup, berhasil maupun gagal
