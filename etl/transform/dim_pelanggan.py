# =====================================================================
# transform/dim_pelanggan.py
# Fungsi : membersihkan master pelanggan (database) dan membentuk dimensi pelanggan.
# Alur   : pilih kolom -> bersihkan id -> hapus duplikat -> rapikan nama
#          -> seragamkan kota -> seragamkan telepon -> surrogate key -> baris default.
# =====================================================================
import logging
import re                                       # regex untuk membersihkan nomor telepon
import pandas as pd

log = logging.getLogger(__name__)

# Langkah 1: peta singkatan / penulisan lain yang disatukan ke nama kota baku
# (kunci memakai format title case karena kota sudah di-title-case sebelum dipetakan)
KOTA_PETA = {
    "Mlg": "Malang",
    "Sby": "Surabaya",
    "Sda": "Sidoarjo",
    "Dki Jakarta": "Jakarta",
}

# Langkah 2: fungsi normalisasi telepon, dipakai per baris lewat .apply()
def normalisasi_telepon(nilai):
    if pd.isna(nilai):                          # telepon kosong tetap kosong
        return pd.NA

    digit = re.sub(r"\D", "", str(nilai))       # buang semua karakter selain angka (spasi, tanda -, +, kurung)
    if digit.startswith("62"):                  # awalan kode negara 62 dibuang
        digit = digit[2:]
    elif digit.startswith("0"):                 # atau awalan 0 lokal dibuang
        digit = digit[1:]
    digit = digit.lstrip("0")                   # sisa angka 0 di depan juga dibuang

    if not 8 <= len(digit) <= 13:               # panjang di luar 8-13 digit dianggap tidak valid
        return pd.NA
    return "+62" + digit                        # format akhir seragam: +62xxxxxxxxxx

def build_dim_pelanggan(df_pelanggan):
    """Membersihkan master pelanggan dan membentuk surrogate key."""
    # Langkah 3: ambil kolom yang dibutuhkan pada salinan data
    kolom = ["id_pelanggan", "nama", "kota", "telepon"]
    df = df_pelanggan[kolom].copy()
    log.info("Pelanggan dibaca: %d baris", len(df))

    # Langkah 4: bersihkan id, ubah placeholder menjadi kosong, buang baris tanpa id
    df["id_pelanggan"] = (
        df["id_pelanggan"].astype("string").str.strip().str.upper()    # buang spasi dan jadikan huruf kapital
    )
    # nilai placeholder (kosong, "NULL", "NONE", "NAN", "-") dianggap data kosong
    df = df.replace({"": pd.NA, "NULL": pd.NA, "NONE": pd.NA, "NAN": pd.NA, "-": pd.NA})
    df = df.dropna(subset=["id_pelanggan"])     # pelanggan tanpa id tidak bisa dikenali, dibuang

    # Langkah 5: hapus duplikat berdasarkan id_pelanggan lalu urutkan
    n_sebelum = len(df)
    df = df.drop_duplicates(subset=["id_pelanggan"]).sort_values("id_pelanggan")
    log.info("Hapus duplikat id_pelanggan: %d baris", n_sebelum - len(df))

    # Langkah 6: rapikan nama (spasi, spasi ganda, huruf kapital di awal kata, isi yang kosong)
    df["nama_pelanggan"] = (
        df["nama"].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)   # spasi ganda jadi satu
        .str.title().fillna("Tanpa Nama")                                              # title case; kosong -> "Tanpa Nama"
    )

    # Langkah 7: seragamkan nama kota
    variasi_awal = df["kota"].dropna().nunique()    # jumlah variasi penulisan sebelum diseragamkan
    df["kota"] = (
        df["kota"].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
        .str.title()
        .str.replace(r"^Kota\s+", "", regex=True)   # "Kota Malang" -> "Malang"
        .replace(KOTA_PETA)                          # "Mlg" -> "Malang", dst.
        .fillna("Tidak Diketahui")                   # kota kosong diberi label baku
    )
    df["kota"] = df["kota"].replace("", "Tidak Diketahui")   # string kosong yang tersisa juga diberi label baku
    log.info("Seragamkan nama kota: %d variasi penulisan -> %d kota",
             variasi_awal, df.loc[df["kota"] != "Tidak Diketahui", "kota"].nunique())
    log.info("Isi kota kosong dengan 'Tidak Diketahui'")

    # Langkah 8: seragamkan telepon ke format +62 memakai fungsi di atas
    df["telepon"] = df["telepon"].apply(normalisasi_telepon)
    log.info("Seragamkan format telepon ke +62")

    # Langkah 9: surrogate key berurutan mulai 1, lalu pilih kolom akhir dimensi
    df.insert(0, "pelanggan_key", range(1, len(df) + 1))
    log.info("Buat surrogate key pelanggan_key")
    dim = df[["pelanggan_key", "id_pelanggan", "nama_pelanggan", "kota", "telepon"]]

    # Langkah 10: baris default (key 0) untuk transaksi yang id pelanggannya tidak ditemukan
    baris_default = pd.DataFrame([{
        "pelanggan_key": 0,
        "id_pelanggan": "-",
        "nama_pelanggan": "Tidak Diketahui",
        "kota": "Tidak Diketahui",
        "telepon": pd.NA,
    }])
    return pd.concat([baris_default, dim], ignore_index=True)    # baris default berada di urutan pertama
