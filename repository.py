"""Akses MySQL untuk aplikasi inventaris Media Com."""

import os
import threading
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DATABASE = "inventaris_mediacom"
_database_ready = False
_database_lock = threading.Lock()


class Session:
    """Adapter tipis agar query lama yang memakai placeholder ? tetap berfungsi."""

    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        cursor = self.connection.cursor()
        cursor.execute(sql.replace("?", "%s"), params)
        return cursor

    def executemany(self, sql, rows):
        cursor = self.connection.cursor()
        cursor.executemany(sql.replace("?", "%s"), rows)
        return cursor


def _connect_server(database=None):
    return pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
                           password=MYSQL_PASSWORD, database=database,
                           charset="utf8mb4", cursorclass=DictCursor,
                           autocommit=False)


def connect_db():
    global _database_ready
    if not _database_ready:
        with _database_lock:
            if not _database_ready:
                server = _connect_server()
                try:
                    with server.cursor() as cursor:
                        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    server.commit()
                    _database_ready = True
                finally:
                    server.close()
    return Session(_connect_server(MYSQL_DATABASE))


@contextmanager
def db_session():
    connection = connect_db()
    try:
        yield connection
        connection.connection.commit()
    except Exception:
        connection.connection.rollback()
        raise
    finally:
        connection.connection.close()


def _table_count(db, table):
    return db.execute(f"SELECT COUNT(*) AS total FROM `{table}`").fetchone()["total"]


def _table_exists(db, table):
    return bool(db.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema=DATABASE() AND table_name=?
    """, (table,)).fetchone())


def _rename_old_tables(db):
    """Pindahkan tabel versi lama ke nama Indonesia tanpa mengubah baris."""
    for old, new in (("users", "pengguna"), ("items", "barang"),
                     ("barang-barang", "barang"), ("loans", "pinjaman")):
        has_old = _table_exists(db, old)
        has_new = _table_exists(db, new)
        if has_old and has_new:
            raise RuntimeError(
                f"Database memiliki tabel `{old}` dan `{new}` sekaligus. "
                "Satukan datanya terlebih dahulu agar tidak ada data yang tertimpa."
            )
        if has_old:
            db.execute(f"RENAME TABLE `{old}` TO `{new}`")


def init_db():
    with db_session() as db:
        _rename_old_tables(db)
        db.execute("""CREATE TABLE IF NOT EXISTS ruangan (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(100) NOT NULL UNIQUE, name VARCHAR(255) NOT NULL UNIQUE,
            person_in_charge VARCHAR(255) NOT NULL DEFAULT '', notes TEXT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        db.execute("""CREATE TABLE IF NOT EXISTS pengguna (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL, username VARCHAR(191) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL, role VARCHAR(30) NOT NULL,
            room_id INT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_pengguna_ruangan FOREIGN KEY (room_id) REFERENCES ruangan(id) ON DELETE SET NULL,
            UNIQUE KEY unique_pembimbing_room (room_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        db.execute("""CREATE TABLE IF NOT EXISTS barang (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(100) NOT NULL UNIQUE, name VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL, room_id INT NULL,
            `condition` VARCHAR(100) NOT NULL DEFAULT 'Baik',
            status VARCHAR(100) NOT NULL DEFAULT 'Tersedia',
            CONSTRAINT fk_barang_ruangan FOREIGN KEY (room_id) REFERENCES ruangan(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        db.execute("""CREATE TABLE IF NOT EXISTS pinjaman (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(100) NOT NULL UNIQUE, item_id INT NOT NULL,
            borrower VARCHAR(255) NOT NULL, borrow_date VARCHAR(40) NOT NULL,
            due_date VARCHAR(40) NOT NULL, returned_at VARCHAR(40) NULL,
            return_condition VARCHAR(100) NULL, origin_room_id INT NULL,
            destination_room_id INT NULL, returned_room_id INT NULL,
            status VARCHAR(100) NOT NULL DEFAULT 'Dipinjam',
            CONSTRAINT fk_pinjaman_barang FOREIGN KEY (item_id) REFERENCES barang(id),
            CONSTRAINT fk_pinjaman_asal FOREIGN KEY (origin_room_id) REFERENCES ruangan(id) ON DELETE SET NULL,
            CONSTRAINT fk_pinjaman_tujuan FOREIGN KEY (destination_room_id) REFERENCES ruangan(id) ON DELETE SET NULL,
            CONSTRAINT fk_pinjaman_kembali FOREIGN KEY (returned_room_id) REFERENCES ruangan(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        if _table_count(db, "ruangan") == 0:
            db.executemany("INSERT INTO ruangan (code, name, person_in_charge) VALUES (?, ?, ?)",
                           [("R-01", "Ruang RPL", "Pembimbing RPL"),
                            ("R-02", "Ruang DKV", "Pembimbing DKV"),
                            ("R-03", "Ruang TKJ", "Pembimbing TKJ"),
                            ("R-04", "Ruang Admin", "Administrator")])
        if _table_count(db, "barang") == 0:
            ruangan = {row["name"]: row["id"] for row in db.execute("SELECT id, name FROM ruangan").fetchall()}
            db.executemany("INSERT INTO barang (code, name, category, room_id, `condition`, status) VALUES (?, ?, ?, ?, ?, ?)",
                           [("INV-001", "Komputer Lenovo ThinkCentre", "Komputer", ruangan["Ruang RPL"], "Baik", "Tersedia"),
                            ("INV-002", "Monitor LED 24 inci", "Monitor", ruangan["Ruang DKV"], "Baik", "Tersedia"),
                            ("INV-003", "Printer Epson L3210", "Printer", ruangan["Ruang Admin"], "Perlu Perbaikan", "Perbaikan"),
                            ("INV-004", "Keyboard Logitech K120", "Aksesori", ruangan["Ruang TKJ"], "Baik", "Tersedia")])


def query_all(sql, params=()):
    with db_session() as db:
        return [dict(row) for row in db.execute(sql, params).fetchall()]


def query_one(sql, params=()):
    with db_session() as db:
        row = db.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(sql, params=()):
    with db_session() as db:
        return db.execute(sql, params).lastrowid


def daftar_barang():
    return query_all("""
        SELECT barang.id, barang.code AS kode, barang.name AS nama,
               barang.category AS kategori, COALESCE(ruangan.name, 'Belum ditempatkan') AS ruangan,
               barang.room_id, barang.`condition` AS kondisi, barang.status
        FROM barang LEFT JOIN ruangan ON ruangan.id = barang.room_id
        ORDER BY barang.code
    """)
