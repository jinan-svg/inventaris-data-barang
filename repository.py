"""Akses MySQL untuk aplikasi inventaris Media Com."""

import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor

ROOT = Path(__file__).resolve().parent
LEGACY_DB_PATH = Path(os.environ.get("INVENTARIS_DB", ROOT / "instance" / "inventaris.db"))
MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "inventaris_mediacom")
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
    if not re.fullmatch(r"[A-Za-z0-9_]+", MYSQL_DATABASE):
        raise ValueError("MYSQL_DATABASE hanya boleh berisi huruf, angka, dan underscore.")
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


def _migrate_sqlite_if_empty(db):
    if not LEGACY_DB_PATH.exists():
        return
    if any(_table_count(db, table) for table in ("users", "rooms", "items", "loans")):
        return
    old = sqlite3.connect(LEGACY_DB_PATH)
    old.row_factory = sqlite3.Row
    try:
        old.execute("PRAGMA foreign_keys = ON")
        for table, columns in (
            ("rooms", ("id", "code", "name", "person_in_charge", "notes")),
            ("users", ("id", "name", "username", "password_hash", "role", "room_id", "created_at")),
            ("items", ("id", "code", "name", "category", "room_id", "condition", "status")),
            ("loans", ("id", "code", "item_id", "borrower", "borrow_date", "due_date", "returned_at", "return_condition", "origin_room_id", "destination_room_id", "returned_room_id", "status")),
        ):
            try:
                rows = old.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
            except sqlite3.OperationalError:
                continue
            if not rows:
                continue
            placeholders = ", ".join(["%s"] * len(columns))
            names = ", ".join(f"`{column}`" for column in columns)
            db.executemany(f"INSERT INTO `{table}` ({names}) VALUES ({placeholders})",
                           [tuple(row[column] for column in columns) for row in rows])
    finally:
        old.close()


def init_db():
    with db_session() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS rooms (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(100) NOT NULL UNIQUE, name VARCHAR(255) NOT NULL UNIQUE,
            person_in_charge VARCHAR(255) NOT NULL DEFAULT '', notes TEXT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL, username VARCHAR(191) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL, role VARCHAR(30) NOT NULL,
            room_id INT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_users_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL,
            UNIQUE KEY unique_pembimbing_room (room_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        db.execute("""CREATE TABLE IF NOT EXISTS items (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(100) NOT NULL UNIQUE, name VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL, room_id INT NULL,
            `condition` VARCHAR(100) NOT NULL DEFAULT 'Baik',
            status VARCHAR(100) NOT NULL DEFAULT 'Tersedia',
            CONSTRAINT fk_items_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        db.execute("""CREATE TABLE IF NOT EXISTS loans (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(100) NOT NULL UNIQUE, item_id INT NOT NULL,
            borrower VARCHAR(255) NOT NULL, borrow_date VARCHAR(40) NOT NULL,
            due_date VARCHAR(40) NOT NULL, returned_at VARCHAR(40) NULL,
            return_condition VARCHAR(100) NULL, origin_room_id INT NULL,
            destination_room_id INT NULL, returned_room_id INT NULL,
            status VARCHAR(100) NOT NULL DEFAULT 'Dipinjam',
            CONSTRAINT fk_loans_item FOREIGN KEY (item_id) REFERENCES items(id),
            CONSTRAINT fk_loans_origin FOREIGN KEY (origin_room_id) REFERENCES rooms(id) ON DELETE SET NULL,
            CONSTRAINT fk_loans_destination FOREIGN KEY (destination_room_id) REFERENCES rooms(id) ON DELETE SET NULL,
            CONSTRAINT fk_loans_returned FOREIGN KEY (returned_room_id) REFERENCES rooms(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        notes_column = db.execute("""
            SELECT IS_NULLABLE FROM information_schema.columns
            WHERE table_schema=DATABASE() AND table_name='rooms' AND column_name='notes'
        """).fetchone()
        if notes_column and notes_column["IS_NULLABLE"] == "NO":
            db.execute("ALTER TABLE rooms MODIFY notes TEXT NULL")
        _migrate_sqlite_if_empty(db)
        if _table_count(db, "rooms") == 0:
            db.executemany("INSERT INTO rooms (code, name, person_in_charge) VALUES (?, ?, ?)",
                           [("R-01", "Ruang RPL", "Pembimbing RPL"),
                            ("R-02", "Ruang DKV", "Pembimbing DKV"),
                            ("R-03", "Ruang TKJ", "Pembimbing TKJ"),
                            ("R-04", "Ruang Admin", "Administrator")])
        if _table_count(db, "items") == 0:
            rooms = {row["name"]: row["id"] for row in db.execute("SELECT id, name FROM rooms").fetchall()}
            db.executemany("INSERT INTO items (code, name, category, room_id, `condition`, status) VALUES (?, ?, ?, ?, ?, ?)",
                           [("INV-001", "Komputer Lenovo ThinkCentre", "Komputer", rooms["Ruang RPL"], "Baik", "Tersedia"),
                            ("INV-002", "Monitor LED 24 inci", "Monitor", rooms["Ruang DKV"], "Baik", "Tersedia"),
                            ("INV-003", "Printer Epson L3210", "Printer", rooms["Ruang Admin"], "Perlu Perbaikan", "Perbaikan"),
                            ("INV-004", "Keyboard Logitech K120", "Aksesori", rooms["Ruang TKJ"], "Baik", "Tersedia")])


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
        SELECT items.id, items.code AS kode, items.name AS nama,
               items.category AS kategori, COALESCE(rooms.name, 'Belum ditempatkan') AS ruangan,
               items.room_id, items.`condition` AS kondisi, items.status
        FROM items LEFT JOIN rooms ON rooms.id = items.room_id
        ORDER BY items.code
    """)
