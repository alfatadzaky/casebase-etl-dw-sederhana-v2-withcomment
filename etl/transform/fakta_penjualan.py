# =====================================================================
# transform/fakta_penjualan.py
# Fungsi : membentuk tabel fakta penjualan (transaksi bersih dengan surrogate
#          key) dan tabel reject (transaksi qty <= 0 beserta alasannya).
# Alur   : salin data -> hapus duplikat -> bersihkan id & tanggal -> filter
#          dimensi waktu -> ubah qty/harga ke angka -> pisahkan reject ->
#          buang data tidak valid -> join ke dimensi -> total_penjualan -> cek PK.
# =====================================================================
import logging

import pandas as pd

from .dim_waktu import parse_tanggal, tanggal_ke_key   # fungsi tanggal dipakai bersama dim_waktu

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# 1. DEFINISI KOLOM
# ---------------------------------------------------------------------
# Kolom asli penjualan.csv, disimpan apa adanya pada tabel reject
KOLOM_MENTAH = [
    "id_transaksi", "tanggal", "id_produk", "id_pelanggan",
    "qty", "harga_satuan", "metode_bayar"
]
KOLOM_REJECT = KOLOM_MENTAH + ["alasan_ditolak"]   # kolom reject = kolom mentah + alasan penolakan

def transform_fakta_penjualan(
    df_penjualan, dim_pelanggan, dim_produk, dim_waktu, dim_metode_bayar
):
    """Membersihkan transaksi dan mengganti ID sumber dengan surrogate key.

    Mengembalikan dua tabel: fakta yang valid, dan reject (transaksi dengan
    qty <= 0 yang disimpan apa adanya agar tetap bisa ditelusuri).
    """
    # Struktur kolom akhir tabel fakta
    kolom_hasil = [ 
        "id_transaksi", "waktu_key", "pelanggan_key", "produk_key",
        "metode_bayar_key", "qty", "harga_satuan", "total_penjualan"
    ]

    # ---------------------------------------------------------------------
    # 2. SALIN DATA DAN KASUS DATA KOSONG
    # ---------------------------------------------------------------------
    df = df_penjualan.copy()                    # salinan kerja agar data mentah asli tidak berubah
    if df.empty:                                # jika tidak ada transaksi, kembalikan dua tabel kosong
        return (
            pd.DataFrame(columns=kolom_hasil),
            pd.DataFrame(columns=KOLOM_REJECT),
        )

    mentah = df_penjualan.copy()    # salinan asli untuk tabel reject (isi tidak akan dibersihkan)

    # ---------------------------------------------------------------------
    # 3. HAPUS BARIS DUPLIKAT
    # ---------------------------------------------------------------------
    n_awal = len(df)
    df = df.drop_duplicates().copy()            # baris yang seluruh kolomnya identik hanya disisakan satu
    log.info("Hapus baris duplikat penjualan: %d baris", n_awal - len(df))

    # ---------------------------------------------------------------------
    # 4. BERSIHKAN ID DAN TANGGAL
    # ---------------------------------------------------------------------
    # Bersihkan ID dan tanggal
    for kolom in ["id_transaksi", "id_produk", "id_pelanggan"]:
        df[kolom] = df[kolom].astype("string").str.strip()      # ke teks dan buang spasi
    df["id_produk"] = df["id_produk"].str.upper()               # huruf kapital agar cocok dengan dimensi
    df["id_pelanggan"] = df["id_pelanggan"].str.upper()
    df["tanggal"] = pd.to_datetime(df["tanggal"].apply(parse_tanggal))   # beragam format tanggal -> satu tipe tanggal
    df["waktu_key"] = tanggal_ke_key(df["tanggal"])             # rumus yyyymmdd yang sama dengan dim_waktu

    # ---------------------------------------------------------------------
    # 5. FILTER BERDASARKAN DIMENSI WAKTU
    # ---------------------------------------------------------------------
    # Transaksi harus memiliki tanggal yang tercatat di dimensi waktu
    n = len(df)
    df = df[df["waktu_key"].isin(dim_waktu["waktu_key"])].copy()   # tanggal tidak terbaca/tidak ada di dimensi dibuang
    log.info("Seragamkan format tanggal: %d baris tanggal tidak valid dibuang", n - len(df))

    # ---------------------------------------------------------------------
    # 6. UBAH QTY DAN HARGA MENJADI ANGKA
    # ---------------------------------------------------------------------
    # Ubah qty dan harga menjadi angka
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce")       # teks non-angka menjadi kosong (NaN), bukan error
    harga = (
        df["harga_satuan"].astype("string")
        .str.replace("Rp", "", regex=False)     # buang simbol Rp
        .str.replace(".", "", regex=False)      # buang pemisah ribuan "."
        .str.replace(",", "", regex=False)      # buang koma
        .str.strip()                            # buang spasi sisa
    )
    df["harga_satuan"] = pd.to_numeric(harga, errors="coerce")  # "Rp 15.000" -> 15000; gagal -> kosong

    # ---------------------------------------------------------------------
    # 7. PISAHKAN TRANSAKSI qty <= 0 KE TABEL REJECT
    # ---------------------------------------------------------------------
    # Transaksi dengan qty <= 0 tidak masuk fakta, tetapi disimpan ke tabel reject.
    # Yang dicatat adalah baris aslinya (sebelum dibersihkan), bukan versi hasil olahan.
    qty_tidak_positif = df["qty"] <= 0                          # penanda (True/False) baris dengan qty nol atau negatif
    reject = mentah.loc[df.index[qty_tidak_positif], KOLOM_MENTAH].copy()   # ambil baris asli lewat indeks yang sama
    reject["alasan_ditolak"] = "qty <= 0"                       # kolom alasan penolakan
    reject = reject.sort_values("id_transaksi", kind="stable").reset_index(drop=True)   # urutkan agar mudah ditelusuri
    df = df[~qty_tidak_positif].copy()                          # baris reject dikeluarkan dari data fakta
    log.info("Pisahkan qty <= 0 ke tabel reject: %d baris", len(reject))

    # ---------------------------------------------------------------------
    # 8. BUANG DATA TIDAK VALID YANG TERSISA
    # ---------------------------------------------------------------------
    # Sisanya hanya transaksi dengan ID, qty, dan harga yang valid
    n = len(df)
    df = df.dropna(subset=["id_transaksi", "qty", "harga_satuan"])   # id, qty, atau harga kosong dibuang
    df = df[df["harga_satuan"] >= 0].copy()                          # harga negatif dibuang
    log.info("Buang ID kosong atau harga tidak valid: %d baris", n - len(df))

    # ---------------------------------------------------------------------
    # 9. JOIN KE DIMENSI UNTUK MENGAMBIL SURROGATE KEY
    # ---------------------------------------------------------------------
    # Gabungkan pelanggan
    peta_pelanggan = dim_pelanggan[["id_pelanggan", "pelanggan_key"]].copy()   # tabel peta id -> key
    peta_pelanggan["id_pelanggan"] = peta_pelanggan["id_pelanggan"].astype("string").str.upper()
    # left join: transaksi tanpa pasangan tetap dipertahankan (key kosong, nanti diarahkan ke 0)
    # validate="many_to_one": satu id harus cocok dengan paling banyak satu baris dimensi, jika tidak error
    df = df.merge(peta_pelanggan, on="id_pelanggan", how="left", validate="many_to_one")

    # Gabungkan produk
    peta_produk = dim_produk[["id_produk", "produk_key"]].copy()
    peta_produk["id_produk"] = peta_produk["id_produk"].astype("string").str.upper()
    df = df.merge(peta_produk, on="id_produk", how="left", validate="many_to_one")

    # Gabungkan metode pembayaran
    df["metode_bayar"] = (
        df["metode_bayar"].astype("string").str.strip().str.upper()    # samakan format dengan dimensi
        .fillna("Tidak Diketahui").replace("", "Tidak Diketahui")      # kosong -> label baku
    )
    df = df.merge(
        dim_metode_bayar[["metode_bayar", "metode_bayar_key"]],
        on="metode_bayar", how="left", validate="many_to_one"
    )

    # ---------------------------------------------------------------------
    # 10. ID TIDAK DITEMUKAN -> BARIS DEFAULT (KEY 0)
    # ---------------------------------------------------------------------
    # ID yang tidak ditemukan diarahkan ke baris default (key 0)
    log.info("Ganti ID sumber dengan surrogate key (waktu, pelanggan, produk, metode bayar)")
    log.info("Pelanggan kosong / tidak ada di master -> key 0: %d baris", int(df["pelanggan_key"].isna().sum()))
    log.info("Produk tidak ada di master -> key 0: %d baris", int(df["produk_key"].isna().sum()))
    log.info("Metode bayar tidak ada di dimensi -> key 0: %d baris", int(df["metode_bayar_key"].isna().sum()))
    for kolom in ["pelanggan_key", "produk_key", "metode_bayar_key"]:
        df[kolom] = df[kolom].fillna(0).astype(int)    # key kosong akibat left join menjadi 0, tipe bilangan bulat

    # ---------------------------------------------------------------------
    # 11. KONVERSI TIPE AKHIR DAN TOTAL PENJUALAN
    # ---------------------------------------------------------------------
    df["waktu_key"] = df["waktu_key"].astype(int)
    df["qty"] = df["qty"].astype(int)
    df["harga_satuan"] = df["harga_satuan"].astype(int)
    df["total_penjualan"] = df["qty"] * df["harga_satuan"]      # ukuran turunan: qty x harga satuan
    log.info("Hitung total_penjualan = qty x harga_satuan")

    hasil = df[kolom_hasil].copy()              # pilih dan urutkan kolom sesuai struktur tabel fakta

    # ---------------------------------------------------------------------
    # 12. VALIDASI PRIMARY KEY KOMPOSIT
    # ---------------------------------------------------------------------
    # PK komposit pada skema adalah (id_transaksi, produk_key).
    duplikat_pk = hasil.duplicated(["id_transaksi", "produk_key"]).sum()   # hitung kombinasi yang berulang
    if duplikat_pk:                             # jika ada, hentikan ETL sebelum Load agar PK tidak gagal di database
        raise ValueError(
            f"Ditemukan {duplikat_pk} baris dengan kombinasi id_transaksi dan "
            "produk_key yang sama. Periksa grain transaksi sebelum load."
        )

    log.info("Fakta penjualan: %s baris", len(hasil))
    log.info("Total penjualan: %s", hasil["total_penjualan"].sum())
    return hasil, reject                        # dua keluaran: fakta valid dan reject
