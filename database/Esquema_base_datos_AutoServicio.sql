CREATE DATABASE AutoServicio_db;
USE AutoServicio_db;
CREATE TABLE departamentos (
    id_departamentos INTEGER PRIMARY KEY AUTO_INCREMENT,
    nombre_departamento VARCHAR(45),
    vlan_id INTEGER,
    rango_red VARCHAR(18) -- Cambiado de INET a VARCHAR para MariaDB
);
CREATE TABLE catalogo_servicios (
    id_servicio INTEGER PRIMARY KEY AUTO_INCREMENT,
    nombre_servicio VARCHAR(45),
    puerto_firewall INTEGER,
    vmid_plantilla INTEGER
);
CREATE TABLE usuarios (
    id_usuario INTEGER PRIMARY KEY AUTO_INCREMENT,
    nombre_usuario VARCHAR(45),
    password_hash VARCHAR(120),
    rol VARCHAR(20), 
    activo BOOLEAN DEFAULT TRUE
);
CREATE TABLE registro_despliegues (
    vmid_proxmox INTEGER PRIMARY KEY,
    ip_asignada VARCHAR(15), -- Cambiado de INET a VARCHAR
    estado VARCHAR(25) CHECK (estado IN ('CREANDO', 'CONFIGURANDO', 'ACTIVO', 'ERROR')),
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP, -- ¡Para la auditoría!
    id_servicio INTEGER,
    id_departamentos INTEGER,
    id_usuario INTEGER,
    FOREIGN KEY (id_departamentos) REFERENCES departamentos(id_departamentos),
    FOREIGN KEY (id_servicio) REFERENCES catalogo_servicios(id_servicio),
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
);