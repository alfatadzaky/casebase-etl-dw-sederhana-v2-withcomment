-- Skema bintang TokoMaju (database tujuan: tokomaju_dw)
DROP TABLE IF EXISTS reject_fakta_penjualan;
DROP TABLE IF EXISTS fakta_penjualan;
DROP TABLE IF EXISTS dim_metode_bayar;
DROP TABLE IF EXISTS dim_waktu;
DROP TABLE IF EXISTS dim_produk;
DROP TABLE IF EXISTS dim_pelanggan;

CREATE TABLE dim_waktu (
    waktu_key INT PRIMARY KEY,
    tanggal DATE NOT NULL,
    hari VARCHAR(10) NOT NULL,
    bulan VARCHAR(15) NOT NULL,
    kuartal VARCHAR(2) NOT NULL,
    tahun INT NOT NULL
);

CREATE TABLE dim_produk (
    produk_key INT PRIMARY KEY,
    id_produk VARCHAR(20) NOT NULL,
    nama_produk VARCHAR(150) NOT NULL,
    kategori VARCHAR(80) NOT NULL,
    merek VARCHAR(80) NOT NULL
);
 
CREATE TABLE dim_pelanggan (
    pelanggan_key INT PRIMARY KEY,
    id_pelanggan VARCHAR(20) NOT NULL,
    nama_pelanggan VARCHAR(150) NOT NULL,
    kota VARCHAR(80) NOT NULL,
    telepon VARCHAR(25)
);

CREATE TABLE dim_metode_bayar (
    metode_bayar_key INT PRIMARY KEY,
    metode_bayar VARCHAR(40) NOT NULL
);

CREATE TABLE fakta_penjualan (
    id_transaksi VARCHAR(20) NOT NULL,
    waktu_key INT NOT NULL REFERENCES dim_waktu(waktu_key),
    pelanggan_key INT NOT NULL REFERENCES dim_pelanggan(pelanggan_key),
    produk_key INT NOT NULL REFERENCES dim_produk(produk_key),
    metode_bayar_key INT NOT NULL REFERENCES dim_metode_bayar(metode_bayar_key),
    qty INT NOT NULL CHECK (qty > 0),
    harga_satuan NUMERIC(12,0) NOT NULL,
    total_penjualan NUMERIC(14,0) NOT NULL,
    PRIMARY KEY (id_transaksi, produk_key)
);

-- Tabel reject: transaksi dengan qty <= 0 yang ditolak dari fakta, disimpan apa adanya
-- (teks mentah) beserta alasannya. Sengaja tanpa PK dan FK.
CREATE TABLE reject_fakta_penjualan (
    id_transaksi VARCHAR(20),
    tanggal VARCHAR(30),
    id_produk VARCHAR(20),
    id_pelanggan VARCHAR(20),
    qty VARCHAR(20),
    harga_satuan VARCHAR(30),
    metode_bayar VARCHAR(40),
    alasan_ditolak VARCHAR(200) NOT NULL
);