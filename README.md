# Inventaris Media Com

Aplikasi inventaris sederhana dengan Flask dan MySQL Laragon.

## Menjalankan aplikasi

1. Jalankan Laragon dan pastikan layanan MySQL aktif.
2. Aktifkan virtual environment project.
3. Instal dependensi dengan `pip install -r requirements.txt`.
4. Secara default aplikasi memakai MySQL Laragon di `127.0.0.1:3306`, user `root`, password kosong, dan membuat database `inventaris_mediacom` otomatis. Skema SQL juga tersedia di `database/schema.sql`. Jika konfigurasi Laragon berbeda, atur variabel lingkungan `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, dan `MYSQL_DATABASE`.
5. Jalankan `python main.py`, lalu buka `http://127.0.0.1:5000`.
6. Jika belum ada Admin, buat akun pertama dengan `flask --app main create-admin`. Admin selanjutnya dapat dibuat dari menu **Pengguna**.

Saat aplikasi pertama kali dijalankan, data dari `instance/inventaris.db` lama disalin ke MySQL jika database tujuan benar-benar kosong. File SQLite lama tidak dihapus. Ruangan dan inventaris contoh ditambahkan hanya jika tabel terkait kosong. Database operasional MySQL tetap berada di komputer Laragon; jangan commit dump yang berisi akun, hash password, atau inventaris internal ke GitHub.

Pendaftaran publik ditutup. Admin membuat dan mengelola maksimal 2 akun Admin serta 4 akun Pembimbing melalui menu **Pengguna**. Setiap Pembimbing harus mendapat ruangan yang unik. Empat ruangan awal dapat diganti namanya di menu **Ruangan**. Akun Admin mengelola pengguna, barang, dan ruangan; Admin maupun Pembimbing dapat mencatat transaksi.

Peminjaman mencatat ruangan asal PC, ruangan tujuan, peminjam, dan tanggal. Lokasi inventaris berubah ke ruangan tujuan selama dipinjam. Pengembalian mencatat kondisi dan ruangan tempat PC dikembalikan.

Untuk penggunaan di luar komputer lokal, atur `SECRET_KEY` dengan nilai acak yang aman dan jalankan aplikasi menggunakan server produksi Flask yang sesuai. Server bawaan `python main.py` ditujukan untuk pengembangan lokal.
