# Inventaris Media Com

Aplikasi inventaris Flask yang memakai satu database MySQL Laragon: `inventaris_mediacom`.

## Menjalankan aplikasi

1. Buka Laragon dan aktifkan MySQL.
2. Aktifkan virtual environment, lalu jalankan `pip install -r requirements.txt`.
3. Jalankan `python main.py` dan buka `http://127.0.0.1:5000`.

Aplikasi otomatis membuat database `inventaris_mediacom` dan tabel yang dibutuhkan (`barang`, `pinjaman`, `ruangan`, `pengguna`) jika belum ada. Data awal ruangan dan barang juga dibuat otomatis. Database lain di Laragon tidak dipakai atau diubah oleh aplikasi ini.

File `database/inventaris_mediacom.sql` adalah snapshot database untuk pemulihan/presentasi. Impor file itu melalui phpMyAdmin hanya ke database kosong; jangan impor ulang ke database yang sudah berisi data.

Jika belum ada akun Admin, buat dari terminal dengan `flask --app main create-admin`. Pendaftaran publik ditutup. Admin mengelola akun, barang, dan ruangan; Admin serta Pembimbing dapat mencatat peminjaman dan pengembalian.

Untuk mengganti koneksi Laragon, atur `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, dan `MYSQL_PASSWORD`. Nama database tetap `inventaris_mediacom` agar aplikasi tidak membuat database kedua.
