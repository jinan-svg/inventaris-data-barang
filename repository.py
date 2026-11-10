"""Akses data SQLite sederhana untuk aplikasi inventaris Media Com."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("INVENTARIS_DB", ROOT / "instance" / "inventaris.db"))


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def db_session():
    connection = connect_db()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db():
    with db_session() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('Admin', 'Pembimbing')),
                room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL UNIQUE,
                person_in_charge TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
                condition TEXT NOT NULL DEFAULT 'Baik',
                status TEXT NOT NULL DEFAULT 'Tersedia'
                    CHECK (status IN ('Tersedia', 'Dipinjam', 'Perbaikan'))
            );
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                item_id INTEGER NOT NULL REFERENCES items(id),
                borrower TEXT NOT NULL,
                borrow_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                returned_at TEXT,
                return_condition TEXT,
                origin_room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
                destination_room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
                returned_room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
                status TEXT NOT NULL DEFAULT 'Dipinjam'
                    CHECK (status IN ('Dipinjam', 'Dikembalikan'))
            );
        """)
        user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
        if "room_id" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL")
        loan_columns = {row["name"] for row in db.execute("PRAGMA table_info(loans)")}
        for column in ("origin_room_id", "destination_room_id", "returned_room_id"):
            if column not in loan_columns:
                db.execute(f"ALTER TABLE loans ADD COLUMN {column} INTEGER REFERENCES rooms(id) ON DELETE SET NULL")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_pembimbing_room ON users(room_id) WHERE role='Pembimbing' AND room_id IS NOT NULL")
        if db.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 0:
            db.executemany(
                "INSERT INTO rooms (code, name, person_in_charge) VALUES (?, ?, ?)",
                [("R-01", "Ruang RPL", "Pembimbing RPL"),
                 ("R-02", "Ruang DKV", "Pembimbing DKV"),
                 ("R-03", "Ruang TKJ", "Pembimbing TKJ"),
                 ("R-04", "Ruang Admin", "Administrator")],
            )
        if db.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0:
            rooms = {row["name"]: row["id"] for row in db.execute("SELECT id, name FROM rooms")}
            db.executemany(
                "INSERT INTO items (code, name, category, room_id, condition, status) VALUES (?, ?, ?, ?, ?, ?)",
                [("INV-001", "Komputer Lenovo ThinkCentre", "Komputer", rooms["Ruang RPL"], "Baik", "Tersedia"),
                 ("INV-002", "Monitor LED 24 inci", "Monitor", rooms["Ruang DKV"], "Baik", "Tersedia"),
                 ("INV-003", "Printer Epson L3210", "Printer", rooms["Ruang Admin"], "Perlu Perbaikan", "Perbaikan"),
                 ("INV-004", "Keyboard Logitech K120", "Aksesori", rooms["Ruang TKJ"], "Baik", "Tersedia")],
            )


def query_all(sql, params=()):
    db = connect_db()
    try:
        return [dict(row) for row in db.execute(sql, params).fetchall()]
    finally:
        db.close()


def query_one(sql, params=()):
    db = connect_db()
    try:
        row = db.execute(sql, params).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def execute(sql, params=()):
    db = connect_db()
    try:
        cursor = db.execute(sql, params)
        db.commit()
        return cursor.lastrowid
    finally:
        db.close()


def daftar_barang():
    return query_all("""
        SELECT items.id, items.code AS kode, items.name AS nama,
               items.category AS kategori, COALESCE(rooms.name, 'Belum ditempatkan') AS ruangan,
               items.room_id, items.condition AS kondisi, items.status
        FROM items LEFT JOIN rooms ON rooms.id = items.room_id
        ORDER BY items.code
    """)
