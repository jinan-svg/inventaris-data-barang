# Inventaris Media Com

Aplikasi inventaris sederhana dengan Flask dan SQLite.

## Menjalankan aplikasi

1. Aktifkan virtual environment project.
2. Jika Flask belum tersedia, jalankan `pip install -r requirements.txt`.
3. Jalankan `python main.py` lalu buka `http://127.0.0.1:5000`.
4. Jika belum ada akun Admin, buat Admin pertama dari terminal dengan `flask --app main create-admin`, lalu ikuti prompt nama, username, dan password. Jika Admin sudah ada, minta Admin tersebut membuat akun dari menu **Pengguna**.

Database dibuat otomatis di `instance/inventaris.db` saat aplikasi dijalankan. Ruangan dan inventaris awal juga ditambahkan otomatis bila tabel masih kosong. Salin file database sebelum melakukan pemindahan atau perubahan besar.

Pendaftaran publik ditutup. Admin membuat dan mengelola maksimal 2 akun Admin serta 4 akun Pembimbing melalui menu **Pengguna**. Setiap Pembimbing harus mendapat ruangan yang unik. Empat ruangan awal dapat diganti namanya di menu **Ruangan**. Akun Admin mengelola pengguna, barang, dan ruangan; Admin maupun Pembimbing dapat mencatat transaksi.

Peminjaman mencatat ruangan asal PC, ruangan tujuan, peminjam, dan tanggal. Lokasi inventaris berubah ke ruangan tujuan selama dipinjam. Pengembalian mencatat kondisi dan ruangan tempat PC dikembalikan.

Untuk penggunaan di luar komputer lokal, atur `SECRET_KEY` dengan nilai acak yang aman dan jalankan aplikasi menggunakan server produksi Flask yang sesuai. Server bawaan `python main.py` ditujukan untuk pengembangan lokal.
