-- Struktur database Inventaris Media Com untuk MySQL 8 / Laragon.
-- Jalankan aplikasi setelah membuat tabel; init_db() akan mengisi empat ruangan
-- dan contoh barang jika tabel terkait masih kosong.

CREATE DATABASE IF NOT EXISTS inventaris_mediacom
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE inventaris_mediacom;

CREATE TABLE IF NOT EXISTS ruangan (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(100) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL UNIQUE,
  person_in_charge VARCHAR(255) NOT NULL DEFAULT '',
  notes TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS users (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  username VARCHAR(191) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(30) NOT NULL,
  room_id INT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_users_room FOREIGN KEY (room_id)
    REFERENCES ruangan(id) ON DELETE SET NULL,
  UNIQUE KEY unique_pembimbing_room (room_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS items (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(100) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  category VARCHAR(100) NOT NULL,
  room_id INT NULL,
  `condition` VARCHAR(100) NOT NULL DEFAULT 'Baik',
  status VARCHAR(100) NOT NULL DEFAULT 'Tersedia',
  CONSTRAINT fk_items_room FOREIGN KEY (room_id)
    REFERENCES ruangan(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS loans (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(100) NOT NULL UNIQUE,
  item_id INT NOT NULL,
  borrower VARCHAR(255) NOT NULL,
  borrow_date VARCHAR(40) NOT NULL,
  due_date VARCHAR(40) NOT NULL,
  returned_at VARCHAR(40) NULL,
  return_condition VARCHAR(100) NULL,
  origin_room_id INT NULL,
  destination_room_id INT NULL,
  returned_room_id INT NULL,
  status VARCHAR(100) NOT NULL DEFAULT 'Dipinjam',
  CONSTRAINT fk_loans_item FOREIGN KEY (item_id) REFERENCES items(id),
  CONSTRAINT fk_loans_origin FOREIGN KEY (origin_room_id)
    REFERENCES ruangan(id) ON DELETE SET NULL,
  CONSTRAINT fk_loans_destination FOREIGN KEY (destination_room_id)
    REFERENCES ruangan(id) ON DELETE SET NULL,
  CONSTRAINT fk_loans_returned FOREIGN KEY (returned_room_id)
    REFERENCES ruangan(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
