from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

@app.route('/login')
def login():
    return render_template('login.html', title="Login")

@app.route('/register')
def register():
    return render_template('register.html', title="Register")

@app.route('/')
def dashboard():
    return render_template('dashboard.html', title="Dashboard")

@app.route('/dataBarang')
def dataBarang():
    return render_template('dataBarang.html', title="Data Barang")

@app.route('/profil-admin')
def profil_admin():
    return render_template('profil_admin.html', title="Profil Admin")

@app.route('/logout')
def logout():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)