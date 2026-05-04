import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import db,Departamento,CatalogoServicio,Usuario,RegistroDespliegue
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
app.secret_key ='KeySecreta'
@app.route('/')
def index():
    return redirect(url_for('login'))
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_form = request.form.get('username').strip()
        password_form = request.form.get('password').strip()
        usuario = Usuario.query.filter_by(nombre_usuario=username_form).first()
        if usuario and check_password_hash(usuario.password_hash,password_form):
            session['nombre_usuario'] = usuario.nombre_usuario
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', mensaje_error='Usuario o contrasenias invalidos.')
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
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username_form = request.form.get('username')
        password_form = request.form.get('password')
        # Vamos a ver si el usuario existe ya dentro de la base de datos
        usuario_existente = Usuario.query.filter_by(nombre_usuario=username_form).first()
        if usuario_existente:
            return render_template('registro.html', mensaje_error="Este usuario ya esta en uso")
        contrasenia_encriptada = generate_password_hash(password_form)
        # Ahora creamos el usuario con la forma de nuestra base de datos, es decir
        nuevo_usuario = Usuario(nombre_usuario=username_form, password_hash=contrasenia_encriptada, rol='usuario_normal', activo=True)
        # Ahora lo metemos en mysql
        db.session.add(nuevo_usuario)
        db.session.commit()
        print("Nuevo usuario registrado exitosamente", username_form)
        return redirect(url_for('login'))
    return render_template('registro.html')
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
