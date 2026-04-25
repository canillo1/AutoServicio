from flask import Flask, render_template, request, redirect, url_for, flash
app = Flask(__name__)
app.secret_key ='KeySecreta'
@app.route('/')
def index():
    return redirect(url_for('login'))
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        password = request.form.get('password')
        if user == "admin" and password == "admin":
            return redirect(url_for('dashboard'))
        else:
            return "Error, Revisa tus credenciales."
    return render_template('login.html')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')
@app.route('/crear_servicio')
def crear_servicio():
    return render_template('crear_servicio.html')
@app.route('/gestionar_servicio')
def gestion_servicio():
    return render_template('gestionar_servicio.html')
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
