import os
import time
import ipaddress
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import db, Departamento, CatalogoServicio, Usuario, RegistroDespliegue
from dotenv import load_dotenv
from proxmox_utils import obtener_servicios_activos, obtener_id_lxc_libre, obtener_ip_libre, conectar_proxmox
from ssh_utils import SSHManager

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
app.secret_key = 'KeySecreta'

app.config['FICHERO_DESCARGADO'] = '/tmp/autoservicio_descargas'
os.makedirs(app.config['FICHERO_DESCARGADO'], exist_ok=True)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_form = request.form.get('username').strip()
        password_form = request.form.get('password').strip()
        usuario = Usuario.query.filter_by(nombre_usuario=username_form).first()
        if usuario and check_password_hash(usuario.password_hash, password_form):
            session['nombre_usuario'] = usuario.nombre_usuario
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', mensaje_error='Usuario o contrasena invalidos.')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'nombre_usuario' not in session:
        return redirect(url_for('login'))
    
    nombre_sesion = session['nombre_usuario']
    usuario_validado = Usuario.query.filter_by(nombre_usuario=nombre_sesion).first()
    
    if not usuario_validado:
        session.clear()
        return redirect(url_for('login'))
    return render_template('dashboard.html', usuario=usuario_validado)

@app.route('/crear_servicio', methods=['GET', 'POST'])
def crear_servicio():
    if 'nombre_usuario' not in session:
        return redirect(url_for('login'))
    if request.method == 'GET':
        return render_template('crear_servicio.html')
        
    tipo_servicio = request.form.get('servicio')    
    plantillas_proxmox = { 'dhcp': 1000, 'dns': 1001, 'web': 1002}
    id_lxc_origen = plantillas_proxmox.get(tipo_servicio)
    
    if not id_lxc_origen:
        flash('Este servicio no se ha encontrado', 'danger')
        return redirect(url_for('dashboard'))
        
    try:
        nuevo_id_lxc = obtener_id_lxc_libre()
        ip_en_uso = [r.ip_asignada for r in RegistroDespliegue.query.all() if r.ip_asignada]
        nueva_ip = obtener_ip_libre(ip_en_uso)
        
        contenido_html = "<h1>Servidor Web Autoservicio</h1>"
        ruta_css = None
        
        if tipo_servicio == 'web':
            fichero_html = request.files.get('fichero_html')
            fichero_css = request.files.get('fichero_css')
            if fichero_html and fichero_html.filename != '':
                nombre_html = secure_filename(fichero_html.filename)
                ruta_html = os.path.join(app.config['FICHERO_DESCARGADO'], str(nuevo_id_lxc), nombre_html)
                os.makedirs(os.path.dirname(ruta_html), exist_ok=True)
                fichero_html.save(ruta_html)
                
                with open(ruta_html, 'r', encoding='utf-8') as f:
                    contenido_html = f.read()
                    
            if fichero_css and fichero_css.filename != '':
                nombre_css = secure_filename(fichero_css.filename)
                ruta_css = os.path.join(app.config['FICHERO_DESCARGADO'], str(nuevo_id_lxc), nombre_css)
                fichero_css.save(ruta_css)
        
        proxmox = conectar_proxmox()
        proxmox.nodes('alejandro').lxc(id_lxc_origen).clone.post(
            newid=nuevo_id_lxc,
            hostname=f"srv-{tipo_servicio}-{nuevo_id_lxc}",
            full=1
        )
        
        print('Clonando', nuevo_id_lxc,'... Esperando a que el disco termine.')
        while True:
            estado_actual = proxmox.nodes('alejandro').lxc(nuevo_id_lxc).status.current.get()
            if estado_actual.get('lock'):
                time.sleep(5)
            else:
                print('Clonado finalizado. Inyectando red...')          
                break
                
        gateway = os.getenv('IP_GATEWAY', '192.168.1.1')
        mascara = os.getenv('IP_MASCARA', '24')
        config_red = f"name=eth0,bridge=vmbr0,ip={nueva_ip}/{mascara},gw={gateway}"
        proxmox.nodes('alejandro').lxc(nuevo_id_lxc).config.put(net0=config_red)
        
        proxmox.nodes('alejandro').lxc(nuevo_id_lxc).status.start.post()

        orquestador = SSHManager(ip=nueva_ip, password=os.getenv('SSH_PASS'))
        exito_ssh = False
        logs_ssh = ""

        if tipo_servicio == 'dhcp':
            ip_ini = request.form.get('dhcp_inicio')
            ip_f = request.form.get('dhcp_fin')
            mask_net = request.form.get('dhcp_mascara')
            gw = request.form.get('dhcp_gateway')
            dns_srv = request.form.get('dhcp_dns')
            red_obj = ipaddress.IPv4Network(f"{gw}/{mask_net}", strict=False)
            red_net = str(red_obj.network_address)
            exito_ssh, logs_ssh = orquestador.configurar_dhcp(red_net, mask_net, ip_ini, ip_f, gw, dns_srv)
        elif tipo_servicio == 'dns':
            zona = request.form.get('dns_zona')
            host = request.form.get('dns_host')
            tipo = request.form.get('dns_tipo')
            valor = request.form.get('dns_valor')
            ttl = request.form.get('dns_ttl')
            if " " in tipo:
                tipo = tipo.split()[0]
            exito_ssh, logs_ssh = orquestador.configurar_dns("192.168.1.0/24", zona, nueva_ip)
            if exito_ssh:
                exito_ssh, logs_ssh = orquestador.añadir_registro_dns(zona, host, tipo, valor, ttl)
        elif tipo_servicio == 'web':
            lista_archivos_web = [
                {'ruta': '/var/www/html/index.html', 'texto': contenido_html}
            ]
            if ruta_css:
                with open(ruta_css, 'r', encoding='utf-8') as f:
                    contenido_css = f.read()
                    lista_archivos_web.append({'ruta': '/var/www/html/estilos.css', 'texto': contenido_css})
            
            comandos_web = ["systemctl restart apache2"]
            exito_ssh, logs_ssh = orquestador.inyectar_configuracion(lista_archivos_web, comandos_web)

        if not exito_ssh:
            raise Exception(f"Fallo en la inyeccion SSH de {tipo_servicio.upper()}: {logs_ssh}")

        servicio_catalogo = CatalogoServicio.query.filter_by(nombre_servicio=tipo_servicio).first()
        id_del_servicio = servicio_catalogo.id_servicio if servicio_catalogo else 1

        usuario = Usuario.query.filter_by(nombre_usuario=session['nombre_usuario']).first()
        nuevo_registro = RegistroDespliegue(
            vmid_proxmox=nuevo_id_lxc,
            ip_asignada=nueva_ip,
            estado='ACTIVO',
            id_usuario=usuario.id_usuario,
            id_servicio=id_del_servicio
        )
        db.session.add(nuevo_registro)
        db.session.commit()
        
        flash(f"Servicio {tipo_servicio.upper()} creado correctamente en la ip {nueva_ip}", "success")
        return redirect(url_for('gestion_servicio'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en el despliegue {tipo_servicio}: {e}")
        flash(f"Error en el despliegue del servicio: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/dns/anadir_registro', methods=['POST'])
def dns_anadir_registro():
    if 'nombre_usuario' not in session:
        return redirect(url_for('login'))
        
    zona_dominio = request.form.get('zona_dominio')
    nombre_host = request.form.get('nombre_host')
    tipo_registro = request.form.get('tipo_registro')
    valor_destino = request.form.get('valor_destino')
    ttl = request.form.get('ttl', '3600')
    
    if tipo_registro and "A " in tipo_registro:
        tipo_registro = "A"

    try:
        usuario_actual = Usuario.query.filter_by(nombre_usuario=session['nombre_usuario']).first()
        
        servicio_dns = CatalogoServicio.query.filter_by(nombre_servicio='dns').first()
        registro_dns = RegistroDespliegue.query.filter_by(
            id_usuario=usuario_actual.id_usuario,
            id_servicio=servicio_dns.id_servicio,
            estado='ACTIVO'
        ).first()
        
        if not registro_dns:
            flash("No tienes ningun servidor DNS activo configurado para este usuario.", "danger")
            return redirect(url_for('dashboard'))
            
        orquestador = SSHManager(ip=registro_dns.ip_asignada, password=os.getenv("SSH_PASS"))
        exito, resultado = orquestador.añadir_registro_dns(zona_dominio, nombre_host, tipo_registro, valor_destino, ttl)
        
        if exito:
            flash(f"Registro {nombre_host}.{zona_dominio} agregado con exito.", "success")
        else:
            flash(f"Error al escribir en el servidor DNS: {resultado}", "danger")
            
    except Exception as e:
        print(f"Error agregando registro DNS: {e}")
        flash("Error interno al procesar el registro DNS.", "danger")
        
    return redirect(url_for('gestion_servicio'))

@app.route('/gestionar_servicios')
def gestion_servicio():
    if 'nombre_usuario' not in session:
        return redirect(url_for('login'))
    try:
        usuario_actual = Usuario.query.filter_by(nombre_usuario=session['nombre_usuario']).first()
        mis_registros = RegistroDespliegue.query.filter_by(id_usuario=usuario_actual.id_usuario).all()
        mapa_ips = {int(r.vmid_proxmox): r.ip_asignada for r in mis_registros if r.vmid_proxmox}
        todos_contenedores = obtener_servicios_activos()
        mis_contenedores = []
        for ct in todos_contenedores:
            vmid_actual = int(ct.get('vmid', 0))
            if vmid_actual in mapa_ips:
                ct['ip_asignada'] = mapa_ips[vmid_actual]
                mis_contenedores.append(ct)
        if len(mis_contenedores) == 0:
            flash('No tienes ningun servicio activo en este momento.', 'info')
            return redirect(url_for('dashboard'))
        return render_template('gestionar_servicio.html', contenedores=mis_contenedores)
    except Exception as e:
        print(f"Error en gestionar_servicios: {e}")
        flash('Error al obtener la lista de tus servicios.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/accion_servicio/<accion>/<int:vmid>')
def accion_servicio(accion, vmid):
    if 'nombre_usuario' not in session:
        return redirect(url_for('login'))
    try:
        usuario_actual = Usuario.query.filter_by(nombre_usuario=session['nombre_usuario']).first()
        registro = RegistroDespliegue.query.filter_by(id_usuario=usuario_actual.id_usuario, vmid_proxmox=vmid).first()
        if not registro:
            flash('Acceso denegado', 'danger')
            return redirect(url_for('gestion_servicio'))
        proxmox = conectar_proxmox()
        if accion == 'parar':
            proxmox.nodes('alejandro').lxc(vmid).status.stop.post()
            registro.estado = 'APAGADO'
            flash(f'Servicio {vmid} apagado', 'success')
        elif accion == 'reiniciar':
            proxmox.nodes('alejandro').lxc(vmid).status.reboot.post()
            flash(f'Servicio {vmid} reiniciando', 'success')
        elif accion == 'iniciar':
            proxmox.nodes('alejandro').lxc(vmid).status.start.post()
            registro.estado = 'ACTIVO'
            flash(f'Servicio {vmid} iniciado', 'success')
        else:
            flash('Accion no reconocida', 'warning')
        db.session.commit()
    except Exception as e:
        print(f'Error al ejecutar {accion} en {vmid}: {e}')
        flash(f'Error al intentar {accion} el servicio', 'danger')
    time.sleep(10)
    return redirect(url_for('gestion_servicio'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username_form = request.form.get('username')
        password_form = request.form.get('password')
        usuario_existente = Usuario.query.filter_by(nombre_usuario=username_form).first()
        if usuario_existente:
            return render_template('registro.html', mensaje_error="Este usuario ya esta en uso")
        contrasenia_encriptada = generate_password_hash(password_form)
        nuevo_usuario = Usuario(nombre_usuario=username_form, password_hash=contrasenia_encriptada, rol='usuario')
        db.session.add(nuevo_usuario)
        db.session.commit()
        print(f"Nuevo usuario registrado exitosamente: {username_form}")
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
