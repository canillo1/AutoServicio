import os
from flask import Flask, render_template, request, redirect, url_for, session,flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import db,Departamento,CatalogoServicio,Usuario,RegistroDespliegue
from dotenv import load_dotenv
from proxmox_utils import obtener_servicios_activos
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
    if 'nombre_usuario' not in session:
        return redirect(url_for('login'))
   #Vamos a validar que el usuario este en la base de datos.
    nombre_sesion = session['nombre_usuario']
    usuario_validado = Usuario.query.filter_by(nombre_usuario=nombre_sesion).first()
   #Si no borramos la session pues puede ser falsa o estar obsoleta:
    if not usuario_validado:
        session.clear()
        return redirect(url_for('login'))
   #Si ha pasado todos los pasos anteriores, el usuario esta logueado correctamente podra continuar.
    return render_template('dashboard.html', usuario=usuario_validado) #ademas he aniadido una variable usuario=usuario_validado para poder usarla dentro de el html...
@app.route('/crear_servicio')
def crear_servicio():
    return render_template('crear_servicio.html')
@app.route('/gestionar_servicios')
def gestion_servicio():
    # Si el usuario no ha iniciado sesion lo mandamos a login y ganamos en seguridad.
    if 'nombre_usuario' not in session:
        return redirect(url_for('login'))
    # Vemos los servicios activos con la funcion del fichero proxmox_utils
    try:
        contenedores_activos = obtener_servicios_activos() # Asegúrate de que importaste esta función arriba
        # Si esta vacia significa que no hay ninguno activo
        if len(contenedores_activos) == 0:
            flash('No se ha encontrado ningun servicio activo', 'warning')
            return redirect(url_for('dashboard'))
        # Si no esta vacio le pasamos los contenedores a la plantilla
        return render_template('gestionar_servicio.html', contenedores=contenedores_activos)
    except Exception as e:
        flash('Error de conexion con Proxmox', 'danger')
        return redirect(url_for('dashboard'))
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
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
