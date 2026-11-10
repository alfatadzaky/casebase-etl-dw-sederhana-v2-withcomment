# =====================================================================
# transform/dim_produk.py
# Fungsi : membersihkan master produk (Excel) dan membentuk dimensi produk.
# Alur   : pilih kolom -> bersihkan teks -> buang id kosong -> hapus duplikat
#          -> seragamkan kategori -> isi nilai kosong -> surrogate key -> baris default.
# =====================================================================
import logging
import pandas as pd

log = logging.getLogger(__name__)

def transform_dim_produk(df_produk):
    """Membersihkan master produk dan membentuk surrogate key."""
    # Langkah 1: ambil hanya kolom yang dibutuhkan, pada salinan agar data mentah tidak berubah
    kolom = ["id_produk", "nama_produk", "kategori", "merek"]
    df = df_produk[kolom].copy()
    log.info("Produk dibaca: %d baris", len(df))

    # Langkah 2: bersihkan seluruh kolom
    # (variabel "kolom" pada for ini menimpa daftar kolom di atas, tetapi aman karena iterasi
    #  tetap berjalan pada daftar aslinya dan daftar itu tidak dipakai lagi setelahnya)
    for kolom in kolom:
        df[kolom] = df[kolom].astype("string").str.strip()      # ke tipe teks dan buang spasi awal/akhir

    df = df.replace("", pd.NA)                                  # string kosong dianggap nilai kosong
    df["id_produk"] = df["id_produk"].str.upper()               # id diseragamkan ke huruf kapital
    df = df.dropna(subset=["id_produk"])                        # produk tanpa id tidak bisa dikenali, dibuang

    # Langkah 3: hapus duplikat berdasarkan id_produk, urutkan, catat jumlah yang dibuang
    n_sebelum = len(df)
    df = df.drop_duplicates(subset=["id_produk"]).sort_values("id_produk")   # baris pertama tiap id dipertahankan
    log.info("Hapus duplikat id_produk: %d baris", n_sebelum - len(df))

    # Langkah 4: peta variasi penulisan kategori ke nama baku (kunci memakai huruf kecil)
    mapping_kategori = {
        "mamin": "Makanan & Minuman",
        "makanan & minuman": "Makanan & Minuman",
        "rumah tangga": "Rumah Tangga",
        "elektronik": "Elektronik",
        "fashion": "Fashion",
        "olahraga": "Olahraga",
        "kesehatan & kecantikan": "Kesehatan & Kecantikan",
        "kesehatan dan kecantikan": "Kesehatan & Kecantikan",
    }
    # Langkah 5: seragamkan kategori
    variasi_awal = df["kategori"].nunique()                     # jumlah variasi penulisan sebelum diseragamkan
    kategori_bersih = df["kategori"].str.lower()                # huruf kecil agar cocok dengan kunci mapping
    df["kategori"] = kategori_bersih.map(mapping_kategori).fillna(
        df["kategori"].str.title()                              # kategori di luar mapping tetap dipakai (title case)
    )
    log.info("Seragamkan kategori: %d variasi penulisan -> %d kategori",
             variasi_awal, df["kategori"].nunique())

    # Langkah 6: isi nilai kosong dengan "Tidak Diketahui" (jumlahnya dicatat dulu pada log)
    kosong = ", ".join(
        f"{k}={int(df[k].isna().sum())}" for k in ["nama_produk", "kategori", "merek"]
    )
    for kolom in ["nama_produk", "kategori", "merek"]:
        df[kolom] = df[kolom].fillna("Tidak Diketahui")
    log.info("Isi nilai kosong dengan 'Tidak Diketahui': %s", kosong)

    # Langkah 7: surrogate key berurutan mulai 1, diletakkan di kolom pertama
    df.insert(0, "produk_key", range(1, len(df) + 1))
    log.info("Buat surrogate key produk_key")

    # Langkah 8: baris default (key 0) untuk transaksi yang id_produk-nya tidak ditemukan
    baris_default = pd.DataFrame([{
        "produk_key": 0,
        "id_produk": "-",
        "nama_produk": "Tidak Diketahui",
        "kategori": "Tidak Diketahui",
        "merek": "Tidak Diketahui",
    }])

    # Gabungkan baris default + dimensi, lalu tetapkan urutan kolom akhir
    return pd.concat([baris_default, df], ignore_index=True)[
        ["produk_key", "id_produk", "nama_produk", "kategori", "merek"]
    ]
