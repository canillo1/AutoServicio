from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
db = SQLAlchemy()
class Departamento(db.Model):
    __tablename__ = 'departamentos'
    id_departamentos = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_departamento = db.Column(db.String(45))
    vlan_id = db.Column(db.Integer)
    rango_red = db.Column(db.String(18))
    despliegues = db.relationship('RegistroDespliegue', backref='departamento', lazy=True)
class CatalogoServicio(db.Model):
    __tablename__ = 'catalogo_servicios'
    id_servicio = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_servicio = db.Column(db.String(45))
    puerto_firewall = db.Column(db.Integer)
    vmid_plantilla = db.Column(db.Integer)
    despliegues = db.relationship('RegistroDespliegue', backref='servicio', lazy=True)
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_usuario = db.Column(db.String(45))
    password_hash = db.Column(db.String(255))
    rol = db.Column(db.String(20))
    activo = db.Column(db.Boolean, default=True)
    despliegues = db.relationship('RegistroDespliegue', backref='creador', lazy=True)
class RegistroDespliegue(db.Model):
    __tablename__ = 'registro_despliegues'
    vmid_proxmox = db.Column(db.Integer, primary_key=True)
    ip_asignada = db.Column(db.String(15))
    estado = db.Column(db.String(25))
    fecha_creacion = db.Column(db.DateTime, server_default=func.now())
    id_servicio = db.Column(db.Integer, db.ForeignKey('catalogo_servicios.id_servicio'))
    id_departamentos = db.Column(db.Integer, db.ForeignKey('departamentos.id_departamentos'))
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
