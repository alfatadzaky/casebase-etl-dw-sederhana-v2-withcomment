# =====================================================================
# transform/dim_metode_bayar.py
# Fungsi : membentuk dimensi metode pembayaran.
# Catatan: tidak ada master metode bayar, jadi dimensi dibentuk dari
#          nilai unik kolom metode_bayar pada data penjualan.
# =====================================================================
import logging
import pandas as pd

log = logging.getLogger(__name__)

def build_dim_metode_bayar(df_penjualan):
    """Membuat dimensi metode pembayaran dari nilai unik transaksi."""
    # Langkah 1-2: rapikan teks agar "cash", "Cash", dan "CASH " dianggap satu metode
    metode = (
        df_penjualan["metode_bayar"].astype("string").str.strip().str.upper()   # ke teks, buang spasi, huruf kapital
    )
    # Langkah 3: string kosong jadi NA lalu dibuang, ambil nilai unik, urutkan abjad
    metode = metode.replace("", pd.NA).dropna().drop_duplicates().sort_values()

    log.info("Ambil metode bayar unik: %d (%s)", len(metode), ", ".join(metode))

    # Langkah 4: bentuk DataFrame dimensi lalu buat surrogate key berurutan mulai 1
    dim = pd.DataFrame({"metode_bayar": metode.tolist()})
    dim.insert(0, "metode_bayar_key", range(1, len(dim) + 1))   # kolom key diletakkan paling depan
    log.info("Buat surrogate key metode_bayar_key (+ baris default key 0)")

    # Langkah 5: baris default (key 0) untuk transaksi yang metode bayarnya kosong/tidak terdaftar
    baris_default = pd.DataFrame([{
        "metode_bayar_key": 0,
        "metode_bayar": "Tidak Diketahui",
    }])
    return pd.concat([baris_default, dim], ignore_index=True)    # baris default berada di urutan pertama
