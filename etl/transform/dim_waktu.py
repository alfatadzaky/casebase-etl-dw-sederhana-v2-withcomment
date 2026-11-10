# =====================================================================
# transform/dim_waktu.py
# Fungsi : membentuk dimensi waktu dari tanggal unik pada data penjualan,
#          serta menyediakan parse_tanggal dan tanggal_ke_key yang juga
#          dipakai oleh fakta_penjualan.py (satu sumber kebenaran key waktu).
# =====================================================================
import logging
import re                                       # regex untuk mengenali pola format tanggal
import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# 1. KAMUS NAMA HARI DAN BULAN
# ---------------------------------------------------------------------
# indeks hari pandas (0 = Senin ... 6 = Minggu) -> nama hari bahasa Indonesia
HARI = {
    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
    4: "Jumat", 5: "Sabtu", 6: "Minggu"
}
# nomor bulan -> nama bulan bahasa Indonesia
BULAN = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}
# tiga huruf awal nama bulan (Indonesia dan Inggris) -> nomor bulan, untuk format "15 Mar 2025"
BULAN_SINGKAT = { 
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "may": 5,
    "jun": 6, "jul": 7, "agu": 8, "aug": 8, "sep": 9,
    "okt": 10, "oct": 10, "nov": 11, "des": 12, "dec": 12
}

# ---------------------------------------------------------------------
# 2. PARSE TANGGAL (beragam format -> satu Timestamp)
# ---------------------------------------------------------------------
def parse_tanggal(nilai):
    """Mengenali yyyy-mm-dd, dd/mm/yyyy, dd-mm-yyyy, dan dd Mon yyyy."""
    if pd.isna(nilai):                          # nilai kosong langsung jadi NaT (tanggal kosong)
        return pd.NaT

    teks = str(nilai).strip()                   # pastikan berupa teks tanpa spasi di tepi
    try:
        # Format 1: yyyy-mm-dd (contoh 2025-03-15)
        cocok = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", teks)
        if cocok:
            return pd.Timestamp(int(cocok[1]), int(cocok[2]), int(cocok[3]))   # tahun, bulan, hari

        # Format 2: dd/mm/yyyy atau dd-mm-yyyy (contoh 15/03/2025)
        cocok = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", teks)
        if cocok:
            return pd.Timestamp(int(cocok[3]), int(cocok[2]), int(cocok[1]))   # urutan dibalik: tahun, bulan, hari

        # Format 3: dd Mon yyyy (contoh 15 Mar 2025 atau 15 Agustus 2025)
        cocok = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", teks)
        if cocok:
            bulan = BULAN_SINGKAT.get(cocok[2][:3].lower())    # tiga huruf pertama nama bulan, huruf kecil
            if bulan:
                return pd.Timestamp(int(cocok[3]), bulan, int(cocok[1]))
    except ValueError:                          # tanggal yang tidak ada di kalender (misal 31 Februari)
        return pd.NaT                           # jadi NaT agar proses tidak berhenti

    return pd.NaT                               # format tidak dikenali

# ---------------------------------------------------------------------
# 3. TANGGAL -> SURROGATE KEY yyyymmdd
# ---------------------------------------------------------------------
# Dipisah sebagai fungsi sendiri agar dim_waktu dan fakta memakai rumus yang sama.
def tanggal_ke_key(tanggal):
    return (
        tanggal.dt.year * 10000                 # 2025 -> 20250000
        + tanggal.dt.month * 100                # + 3 bulan -> 20250300
        + tanggal.dt.day                        # + 15 hari -> 20250315
    ).astype("Int64")                           # Int64 mendukung nilai kosong (NaT menjadi <NA>)

# ---------------------------------------------------------------------
# 4. MEMBANGUN DIMENSI WAKTU
# ---------------------------------------------------------------------
def build_dim_waktu(df_penjualan):
    # Langkah 4: ubah kolom tanggal mentah menjadi tipe tanggal, catat yang gagal dibaca
    tanggal = pd.to_datetime(df_penjualan["tanggal"].apply(parse_tanggal))
    log.info("Seragamkan format tanggal: %d baris dibaca, %d tidak terbaca",
             len(tanggal), int(tanggal.isna().sum()))
    # Langkah 5: ambil tanggal unik (buang kosong, samakan jam ke 00:00, hapus duplikat, urut kronologis)
    tanggal_unik = tanggal.dropna().dt.normalize().drop_duplicates().sort_values()

    # Langkah 6: bentuk DataFrame dimensi dan buat surrogate key waktu_key
    dim = tanggal_unik.to_frame("tanggal").reset_index(drop=True)
    dim["waktu_key"] = tanggal_ke_key(dim["tanggal"]).astype(int)
    log.info("Buat surrogate key waktu_key")
    # Langkah 7: turunkan atribut waktu dari tanggal
    dim["hari"] = dim["tanggal"].dt.weekday.map(HARI)               # nama hari
    dim["bulan"] = dim["tanggal"].dt.month.map(BULAN)               # nama bulan
    dim["kuartal"] = "Q" + dim["tanggal"].dt.quarter.astype(str)    # Q1 sampai Q4
    dim["tahun"] = dim["tanggal"].dt.year.astype(int)               # tahun sebagai bilangan bulat
    dim["tanggal"] = dim["tanggal"].dt.date                         # simpan sebagai tanggal tanpa jam

    # Langkah 8: catat jumlah hari dan rentang tanggal
    log.info("Ambil tanggal unik: %d hari (%s sampai %s)",
             len(dim), dim["tanggal"].min(), dim["tanggal"].max())

    return dim[["waktu_key", "tanggal", "hari", "bulan", "kuartal", "tahun"]]   # urutan kolom akhir
