"""Aplikasi inventaris Media Com."""

import csv
import click
import io
import os
import secrets
from datetime import date
from functools import wraps

from flask import (Flask, flash, redirect, render_template, request, send_file,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from repository import db_session, daftar_barang, execute, init_db, query_all, query_one

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-secret")
init_db()


@app.cli.command("create-admin")
def create_admin():
    """Buat akun Admin awal dari terminal, tanpa pendaftaran publik."""
    admin_count = query_one("SELECT COUNT(*) AS jumlah FROM users WHERE role='Admin'")["jumlah"]
    if admin_count >= 2:
        click.echo("Batas 2 akun Admin sudah tercapai.")
        return
    name = click.prompt("Nama Admin").strip()
    username = click.prompt("Username", type=str).strip()
    password = click.prompt("Password (minimal 8 karakter)", hide_input=True, confirmation_prompt=True)
    if not name or not username:
        raise click.ClickException("Nama dan username tidak boleh kosong.")
    if len(password) < 8:
        raise click.ClickException("Password harus terdiri dari minimal 8 karakter.")
    try:
        execute("INSERT INTO users (name, username, password_hash, role) VALUES (?, ?, ?, 'Admin')",
                (name.strip(), username.strip(), generate_password_hash(password)))
    except Exception as error:
        if "UNIQUE" in str(error):
            raise click.ClickException("Username tersebut sudah digunakan.") from error
        raise
    click.echo("Akun Admin berhasil dibuat.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login untuk membuka aplikasi.", "error")
            return redirect(url_for("login"))
        user = query_one("""
            SELECT users.name, users.username, users.role, users.room_id, rooms.name AS room_name
            FROM users LEFT JOIN rooms ON rooms.id=users.room_id WHERE users.id=?
        """, (session["user_id"],))
        if not user:
            session.clear()
            flash("Akun ini sudah tidak aktif. Hubungi Admin Media Com.", "error")
            return redirect(url_for("login"))
        session["name"] = user["name"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["room_id"] = user["room_id"]
        session["room_name"] = user["room_name"]
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role") != "Admin":
            flash("Akses ini hanya tersedia untuk Admin.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        user = query_one("""
            SELECT users.*, rooms.name AS room_name FROM users
            LEFT JOIN rooms ON rooms.id=users.room_id WHERE users.username = ?
        """, (username,))
        if user and user["role"] == role and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            session["room_id"] = user["room_id"]
            session["room_name"] = user["room_name"]
            flash("Berhasil login. Selamat datang!", "success")
            return redirect(url_for("dashboard"))
        flash("Username, password, atau jenis akses tidak cocok.", "error")
    admin_exists = query_one("SELECT COUNT(*) AS jumlah FROM users WHERE role='Admin'")["jumlah"] > 0
    return render_template("login.html", title="Login", admin_exists=admin_exists)


@app.route("/register", methods=["GET", "POST"])
def register():
    flash("Pendaftaran publik ditutup. Minta Admin Media Com membuatkan akun untuk Anda.", "error")
    return redirect(url_for("login"))


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    flash("Anda sudah keluar.", "success")
    return redirect(url_for("login"))


@app.route("/pengguna", methods=["GET", "POST"])
@admin_required
def pengguna():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        room_id = request.form.get("room_id", type=int)
        if not name or not username or len(password) < 8:
            flash("Nama dan username wajib diisi. Password minimal 8 karakter.", "error")
        elif role not in ("Admin", "Pembimbing"):
            flash("Pilih jenis akun yang valid.", "error")
        elif role == "Admin" and query_one("SELECT COUNT(*) AS jumlah FROM users WHERE role='Admin'")["jumlah"] >= 2:
            flash("Batas maksimal 2 akun Admin sudah tercapai.", "error")
        elif role == "Pembimbing" and query_one("SELECT COUNT(*) AS jumlah FROM users WHERE role='Pembimbing'")["jumlah"] >= 4:
            flash("Batas maksimal 4 akun Pembimbing sudah tercapai.", "error")
        elif role == "Pembimbing" and not room_id:
            flash("Setiap akun Pembimbing harus ditugaskan ke satu ruangan.", "error")
        elif role == "Pembimbing" and query_one("SELECT id FROM users WHERE role='Pembimbing' AND room_id=?", (room_id,)):
            flash("Ruangan tersebut sudah memiliki akun Pembimbing.", "error")
        elif role == "Pembimbing" and not query_one("SELECT id FROM rooms WHERE id=?", (room_id,)):
            flash("Pilih ruangan yang tersedia.", "error")
        else:
            try:
                execute("INSERT INTO users (name, username, password_hash, role, room_id) VALUES (?, ?, ?, ?, ?)",
                        (name, username, generate_password_hash(password), role, room_id if role == "Pembimbing" else None))
                flash(f"Akun {role} berhasil dibuat.", "success")
                return redirect(url_for("pengguna"))
            except Exception as error:
                if "UNIQUE" in str(error):
                    flash("Username tersebut sudah digunakan.", "error")
                else:
                    raise
    users = query_all("""
        SELECT users.id, users.name, users.username, users.role, users.room_id,
               rooms.name AS room_name FROM users
        LEFT JOIN rooms ON rooms.id=users.room_id ORDER BY users.role, users.name
    """)
    rooms = query_all("""
        SELECT rooms.id, rooms.name FROM rooms
        WHERE rooms.id NOT IN (
            SELECT room_id FROM users WHERE role='Pembimbing' AND room_id IS NOT NULL
        ) ORDER BY rooms.code
    """)
    counts = {
        "admin": sum(user["role"] == "Admin" for user in users),
        "pembimbing": sum(user["role"] == "Pembimbing" for user in users),
    }
    return render_template("pengguna.html", title="Kelola Pengguna", users=users, rooms=rooms, counts=counts)


@app.post("/pengguna/<int:user_id>/hapus")
@admin_required
def hapus_pengguna(user_id):
    target = query_one("SELECT id, role FROM users WHERE id=?", (user_id,))
    if not target:
        flash("Akun tidak ditemukan.", "error")
    elif user_id == session["user_id"]:
        flash("Akun yang sedang dipakai tidak dapat dihapus.", "error")
    elif target["role"] == "Admin" and query_one("SELECT COUNT(*) AS jumlah FROM users WHERE role='Admin'")["jumlah"] <= 1:
        flash("Admin terakhir tidak dapat dihapus.", "error")
    else:
        execute("DELETE FROM users WHERE id=?", (user_id,))
        flash("Akun berhasil dihapus.", "success")
    return redirect(url_for("pengguna"))


@app.route("/pengguna/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_pengguna(user_id):
    target = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if not target:
        flash("Akun tidak ditemukan.", "error")
        return redirect(url_for("pengguna"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        role = request.form.get("role", "")
        room_id = request.form.get("room_id", type=int)
        admin_count = query_one("SELECT COUNT(*) AS jumlah FROM users WHERE role='Admin' AND id!=?", (user_id,))["jumlah"]
        mentor_count = query_one("SELECT COUNT(*) AS jumlah FROM users WHERE role='Pembimbing' AND id!=?", (user_id,))["jumlah"]
        room_exists = query_one("SELECT id FROM rooms WHERE id=?", (room_id,)) if room_id else None
        room_taken = query_one("SELECT id FROM users WHERE role='Pembimbing' AND room_id=? AND id!=?", (room_id, user_id)) if room_id else None
        if not name or not username:
            flash("Nama dan username wajib diisi.", "error")
        elif role not in ("Admin", "Pembimbing"):
            flash("Pilih jenis akun yang valid.", "error")
        elif role == "Admin" and admin_count >= 2:
            flash("Batas maksimal 2 akun Admin sudah tercapai.", "error")
        elif role == "Pembimbing" and mentor_count >= 4:
            flash("Batas maksimal 4 akun Pembimbing sudah tercapai.", "error")
        elif target["role"] == "Admin" and role != "Admin" and admin_count == 0:
            flash("Admin terakhir tidak dapat diubah menjadi Pembimbing.", "error")
        elif role == "Pembimbing" and (not room_id or not room_exists):
            flash("Setiap Pembimbing harus ditugaskan ke satu ruangan.", "error")
        elif role == "Pembimbing" and room_taken:
            flash("Ruangan tersebut sudah memiliki akun Pembimbing.", "error")
        else:
            try:
                execute("UPDATE users SET name=?, username=?, role=?, room_id=? WHERE id=?",
                        (name, username, role, room_id if role == "Pembimbing" else None, user_id))
                flash("Data akun berhasil diperbarui.", "success")
                return redirect(url_for("pengguna"))
            except Exception as error:
                if "UNIQUE" in str(error):
                    flash("Username tersebut sudah digunakan.", "error")
                else:
                    raise
    rooms = query_all("""
        SELECT rooms.id, rooms.name FROM rooms WHERE rooms.id NOT IN (
            SELECT room_id FROM users WHERE role='Pembimbing' AND room_id IS NOT NULL AND id!=?
        ) ORDER BY rooms.code
    """, (user_id,))
    return render_template("form_pengguna.html", title="Ubah Akun", user=target, rooms=rooms)


@app.post("/pengguna/<int:user_id>/password")
@admin_required
def reset_password_pengguna(user_id):
    password = request.form.get("password", "")
    if not query_one("SELECT id FROM users WHERE id=?", (user_id,)):
        flash("Akun tidak ditemukan.", "error")
    elif len(password) < 8:
        flash("Password baru minimal 8 karakter.", "error")
    else:
        execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(password), user_id))
        flash("Password akun berhasil diperbarui.", "success")
    return redirect(url_for("pengguna"))


@app.route("/")
@login_required
def dashboard():
    barang = daftar_barang()
    ruangan = query_all("""
        SELECT rooms.name, COUNT(items.id) AS total FROM rooms
        LEFT JOIN items ON items.room_id = rooms.id GROUP BY rooms.id ORDER BY rooms.code
    """)
    statistik = {
        "total": len(barang),
        "tersedia": sum(item["status"] == "Tersedia" for item in barang),
        "dipinjam": sum(item["status"] == "Dipinjam" for item in barang),
        "perbaikan": sum(item["status"] == "Perbaikan" for item in barang),
    }
    aktivitas = query_all("""
        SELECT loans.code, loans.borrower, loans.borrow_date, loans.due_date,
               loans.status, items.name AS barang, origin.name AS origin_room,
               destination.name AS destination_room
        FROM loans JOIN items ON items.id = loans.item_id
        LEFT JOIN rooms AS origin ON origin.id=loans.origin_room_id
        LEFT JOIN rooms AS destination ON destination.id=loans.destination_room_id
        ORDER BY loans.id DESC LIMIT 6
    """)
    for room in ruangan:
        room["tinggi"] = max(8, round(room["total"] / max([r["total"] for r in ruangan] or [1]) * 100))
    statistik["persen_tersedia"] = round(statistik["tersedia"] / statistik["total"] * 100) if statistik["total"] else 0
    statistik["persen_dipinjam"] = round(statistik["dipinjam"] / statistik["total"] * 100) if statistik["total"] else 0
    statistik["persen_sampai_dipinjam"] = statistik["persen_tersedia"] + statistik["persen_dipinjam"]
    return render_template("dashboard.html", title="Dashboard", statistik=statistik, aktivitas=aktivitas, ruangan=ruangan)


@app.route("/dataBarang")
@app.route("/data-barang")
@login_required
def data_barang():
    return render_template("dataBarang.html", title="Data Barang", barang=daftar_barang())


@app.route("/barang/tambah", methods=["GET", "POST"])
@app.route("/barang/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def form_barang(item_id=None):
    item = query_one("SELECT * FROM items WHERE id = ?", (item_id,)) if item_id else None
    if item_id and not item:
        flash("Barang tidak ditemukan.", "error")
        return redirect(url_for("data_barang"))
    if request.method == "POST":
        submitted_status = request.form.get("status", "Tersedia")
        if submitted_status not in ("Tersedia", "Perbaikan"):
            flash("Status Dipinjam hanya dapat diubah melalui transaksi peminjaman.", "error")
            return redirect(url_for("data_barang"))
        if item and item["status"] == "Dipinjam":
            submitted_status = "Dipinjam"
        room_id = item["room_id"] if item else request.form.get("room_id") or None
        values = (request.form.get("code", "").strip(), request.form.get("name", "").strip(),
                  request.form.get("category", "").strip(), room_id,
                  request.form.get("condition", "Baik"), submitted_status)
        if not all(values[index] for index in (0, 1, 2)):
            flash("Kode, nama, dan kategori barang wajib diisi.", "error")
        else:
            try:
                if item:
                    execute("UPDATE items SET code=?, name=?, category=?, room_id=?, condition=?, status=? WHERE id=?", (*values, item_id))
                    flash("Data barang berhasil diperbarui.", "success")
                else:
                    execute("INSERT INTO items (code, name, category, room_id, condition, status) VALUES (?, ?, ?, ?, ?, ?)", values)
                    flash("Barang berhasil ditambahkan.", "success")
                return redirect(url_for("data_barang"))
            except Exception as error:
                if "UNIQUE" in str(error):
                    flash("Kode barang sudah digunakan.", "error")
                else:
                    raise
    rooms = query_all("SELECT id, name FROM rooms ORDER BY name")
    return render_template("form_barang.html", title="Edit Barang" if item else "Tambah Barang", item=item, rooms=rooms)


@app.post("/barang/<int:item_id>/hapus")
@admin_required
def hapus_barang(item_id):
    try:
        execute("DELETE FROM items WHERE id = ?", (item_id,))
        flash("Barang berhasil dihapus.", "success")
    except Exception:
        flash("Barang yang memiliki riwayat transaksi tidak dapat dihapus.", "error")
    return redirect(url_for("data_barang"))


@app.route("/peminjaman", methods=["GET", "POST"])
@login_required
def peminjaman():
    if request.method == "POST":
        item_id = request.form.get("item_id", type=int)
        borrower = session["name"] if session.get("role") == "Pembimbing" else request.form.get("borrower", "").strip()
        destination_room_id = session.get("room_id") if session.get("role") == "Pembimbing" else request.form.get("destination_room_id", type=int)
        borrow_date = request.form.get("borrow_date", "")
        due_date = request.form.get("due_date", "")
        item = query_one("SELECT * FROM items WHERE id = ? AND status = 'Tersedia'", (item_id,))
        destination = query_one("SELECT id FROM rooms WHERE id=?", (destination_room_id,)) if destination_room_id else None
        try:
            valid_dates = date.fromisoformat(borrow_date) <= date.fromisoformat(due_date)
        except ValueError:
            valid_dates = False
        if (not item or not destination or item["room_id"] == destination_room_id or not borrower
                or not valid_dates):
            flash("Periksa barang, peminjam, dan tanggal peminjaman.", "error")
        else:
            code = f"PMJ-{date.today():%y%m%d}-{secrets.token_hex(3).upper()}"
            with db_session() as db:
                updated = db.execute(
                    "UPDATE items SET status='Dipinjam', room_id=? WHERE id=? AND status='Tersedia'",
                    (destination_room_id, item_id),
                )
                if updated.rowcount:
                    db.execute("""
                        INSERT INTO loans (code, item_id, borrower, borrow_date, due_date,
                                           origin_room_id, destination_room_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (code, item_id, borrower, borrow_date, due_date, item["room_id"], destination_room_id))
            if not updated.rowcount:
                flash("PC tersebut baru saja dipinjam. Muat ulang daftar barang.", "error")
                return redirect(url_for("peminjaman"))
            flash(f"Peminjaman {code} berhasil dicatat.", "success")
            return redirect(url_for("peminjaman"))
    if session.get("role") == "Pembimbing":
        items = query_all("""
            SELECT items.id, items.code, items.name, items.room_id, rooms.name AS origin_room
            FROM items JOIN rooms ON rooms.id=items.room_id
            WHERE items.status='Tersedia' AND items.room_id != ? ORDER BY items.name
        """, (session.get("room_id"),)) if session.get("room_id") else []
    else:
        items = query_all("""
            SELECT items.id, items.code, items.name, items.room_id, rooms.name AS origin_room
            FROM items JOIN rooms ON rooms.id=items.room_id
            WHERE items.status='Tersedia' ORDER BY items.name
        """)
    rooms = query_all("SELECT id, name FROM rooms ORDER BY code") if session.get("role") == "Admin" else []
    loans = query_all("""
        SELECT loans.*, items.name AS item_name, origin.name AS origin_room,
               destination.name AS destination_room
        FROM loans JOIN items ON items.id = loans.item_id
        LEFT JOIN rooms AS origin ON origin.id=loans.origin_room_id
        LEFT JOIN rooms AS destination ON destination.id=loans.destination_room_id
        ORDER BY loans.id DESC
    """)
    return render_template("peminjaman.html", title="Peminjaman", items=items, rooms=rooms,
                           loans=loans, today=date.today().isoformat())


@app.route("/pengembalian", methods=["GET", "POST"])
@login_required
def pengembalian():
    if request.method == "POST":
        loan_id = request.form.get("loan_id", type=int)
        condition = request.form.get("return_condition", "Baik")
        loan = query_one("SELECT * FROM loans WHERE id = ? AND status = 'Dipinjam'", (loan_id,))
        if loan:
            if condition not in ("Baik", "Perlu Perbaikan", "Rusak"):
                flash("Pilih kondisi komputer yang valid.", "error")
                return redirect(url_for("pengembalian"))
            returned_room_id = request.form.get("returned_room_id", type=int) or loan["origin_room_id"]
            if not query_one("SELECT id FROM rooms WHERE id=?", (returned_room_id,)):
                flash("Pilih ruangan tujuan pengembalian yang valid.", "error")
                return redirect(url_for("pengembalian"))
            item_status = "Tersedia" if condition == "Baik" else "Perbaikan"
            with db_session() as db:
                updated = db.execute("""
                    UPDATE loans SET status='Dikembalikan', returned_at=?, return_condition=?, returned_room_id=?
                    WHERE id=? AND status='Dipinjam'
                """, (date.today().isoformat(), condition, returned_room_id, loan_id))
                if updated.rowcount:
                    db.execute("UPDATE items SET status=?, condition=?, room_id=? WHERE id=?",
                               (item_status, condition, returned_room_id, loan["item_id"]))
            if updated.rowcount:
                flash("Pengembalian berhasil dicatat.", "success")
            else:
                flash("Transaksi tersebut baru saja diproses.", "error")
        else:
            flash("Transaksi peminjaman tidak ditemukan atau sudah ditutup.", "error")
        return redirect(url_for("pengembalian"))
    loans = query_all("""
        SELECT loans.*, items.name AS item_name, origin.name AS origin_room,
               destination.name AS destination_room FROM loans
        JOIN items ON items.id = loans.item_id
        LEFT JOIN rooms AS origin ON origin.id=loans.origin_room_id
        LEFT JOIN rooms AS destination ON destination.id=loans.destination_room_id
        WHERE loans.status='Dipinjam'
        ORDER BY loans.due_date
    """)
    rooms = query_all("SELECT id, name FROM rooms ORDER BY code")
    return render_template("pengembalian.html", title="Pengembalian", loans=loans, rooms=rooms)


@app.route("/ruangan", methods=["GET", "POST"])
@admin_required
def ruangan():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        name = request.form.get("name", "").strip()
        person = request.form.get("person_in_charge", "").strip()
        room_count = query_one("SELECT COUNT(*) AS jumlah FROM rooms")["jumlah"]
        if room_count >= 4:
            flash("Project ini dibatasi untuk 4 ruangan. Ubah ruangan yang sudah ada.", "error")
        elif not code or not name:
            flash("Kode dan nama ruangan wajib diisi.", "error")
        else:
            try:
                execute("INSERT INTO rooms (code, name, person_in_charge) VALUES (?, ?, ?)", (code, name, person))
                flash("Ruangan berhasil ditambahkan.", "success")
                return redirect(url_for("ruangan"))
            except Exception as error:
                if "UNIQUE" in str(error):
                    flash("Kode atau nama ruangan sudah digunakan.", "error")
                else:
                    raise
    rooms = query_all("""
        SELECT rooms.*, COUNT(items.id) AS item_count FROM rooms
        LEFT JOIN items ON items.room_id = rooms.id GROUP BY rooms.id ORDER BY rooms.code
    """)
    return render_template("ruangan.html", title="Data Ruangan", rooms=rooms)


@app.route("/ruangan/<int:room_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_ruangan(room_id):
    room = query_one("SELECT * FROM rooms WHERE id=?", (room_id,))
    if not room:
        flash("Ruangan tidak ditemukan.", "error")
        return redirect(url_for("ruangan"))
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        name = request.form.get("name", "").strip()
        person = request.form.get("person_in_charge", "").strip()
        if not code or not name:
            flash("Kode dan nama ruangan wajib diisi.", "error")
        else:
            try:
                execute("UPDATE rooms SET code=?, name=?, person_in_charge=? WHERE id=?", (code, name, person, room_id))
                flash("Data ruangan berhasil diperbarui.", "success")
                return redirect(url_for("ruangan"))
            except Exception as error:
                if "UNIQUE" in str(error):
                    flash("Kode atau nama ruangan sudah digunakan.", "error")
                else:
                    raise
    return render_template("form_ruangan.html", title="Ubah Ruangan", room=room)


@app.post("/ruangan/<int:room_id>/hapus")
@admin_required
def hapus_ruangan(room_id):
    if query_one("SELECT id FROM users WHERE role='Pembimbing' AND room_id=?", (room_id,)):
        flash("Ruangan ini masih ditugaskan kepada Pembimbing. Pindahkan akunnya terlebih dahulu.", "error")
        return redirect(url_for("ruangan"))
    if query_one("SELECT id FROM items WHERE room_id=?", (room_id,)):
        flash("Ruangan ini masih memiliki inventaris. Pindahkan PC terlebih dahulu.", "error")
        return redirect(url_for("ruangan"))
    if query_one("""
        SELECT id FROM loans WHERE origin_room_id=? OR destination_room_id=? OR returned_room_id=?
    """, (room_id, room_id, room_id)):
        flash("Ruangan ini masih tercatat dalam riwayat peminjaman.", "error")
        return redirect(url_for("ruangan"))
    execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    flash("Ruangan dihapus. Barang terkait dipindahkan ke status belum ditempatkan.", "success")
    return redirect(url_for("ruangan"))


@app.route("/laporan")
@login_required
def laporan():
    barang = daftar_barang()
    loans = query_all("""
        SELECT loans.*, items.name AS item_name, origin.name AS origin_room,
               destination.name AS destination_room, returned.name AS returned_room
        FROM loans JOIN items ON items.id=loans.item_id
        LEFT JOIN rooms AS origin ON origin.id=loans.origin_room_id
        LEFT JOIN rooms AS destination ON destination.id=loans.destination_room_id
        LEFT JOIN rooms AS returned ON returned.id=loans.returned_room_id
        ORDER BY loans.id DESC
    """)
    return render_template("laporan.html", title="Laporan", barang=barang, loans=loans)


@app.route("/laporan.csv")
@login_required
def ekspor_laporan():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Kode", "Nama Barang", "Kategori", "Ruangan", "Kondisi", "Status"])
    for item in daftar_barang():
        writer.writerow([item["kode"], item["nama"], item["kategori"], item["ruangan"], item["kondisi"], item["status"]])
    return send_file(io.BytesIO(output.getvalue().encode("utf-8-sig")), mimetype="text/csv",
                     as_attachment=True, download_name="laporan-inventaris.csv")


@app.route("/profil-admin")
@login_required
def profil_admin():
    admin = query_one("""
        SELECT users.name, users.username, users.role, rooms.name AS room_name
        FROM users LEFT JOIN rooms ON rooms.id=users.room_id WHERE users.id=?
    """, (session["user_id"],))
    admin["nama"] = admin.pop("name")
    admin["jabatan"] = admin["role"]
    return render_template("profile-admin.html", title="Profil", admin=admin)


if __name__ == "__main__":
    app.run(debug=True)
