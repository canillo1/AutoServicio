# AutoServicio: Plataforma de Aprovisionamiento Automatizado sobre Proxmox VE

**Proyecto Final del Ciclo Formativo de Grado Superior en Administración de Sistemas Informáticos en Red (ASIR)**

**Autor:** Alejandro Cano Gil 
**ASIR:** 2025/2026  
**Centro Educativo:** CPIFP Alan Turing  

---

## Descripción del Proyecto

**AutoServicio** es una aplicación web diseñada para automatizar el despliegue, configuración y fortificación de servicios de red e infraestructura (DNS, DHCP, Servidores Web, Mensajería) dentro de una empresa. 

Actuando como un panel de control centralizado (Frontend web) y conectándose nativamente a la API REST de Proxmox VE (Backend en Python), la herramienta permite a los administradores aprovisionar contenedores LXC en cuestión de segundos. El sistema incluye funcionalidades avanzadas como microsegmentación de red (SDN), inyección de configuraciones dinámicas vía SSH, fortificación mediante Proxmox Firewall y protección DNS perimetral con Pi-hole.

---

## Objetivos

1. Transformar los despliegues manuales en un modelo de Infraestructura como Código (IaC).
2. Reducir los tiempos de despliegue de infraestructura en un 90%.
3. Garantizar la seguridad por diseño mediante aislamiento de red y firewalls distribuidos.
4. Mantener una auditoría completa de todas las acciones ejecutadas en el sistema.

---

## Tecnologías Utilizadas

### Infraestructura y Redes (Sistemas)
* **Proxmox VE 8.x:** Hipervisor principal.
* **LXC (Linux Containers):** Virtualización ligera (Ubuntu Server).
* **Proxmox SDN & Firewall:** Microsegmentación y seguridad.
* **Pi-hole:** Sumidero DNS.

### Backend y Lógica
* **Python 3:** Lenguaje principal de orquestación.
* **Flask:** Micro-framework web.
* **Librerías:** `proxmoxer` (API Proxmox), `paramiko` (Conexiones SSH), `pymysql` o `SQLAlchemy` (Base de datos).

### Frontend
* **HTML5, CSS3**
* **Bootstrap 5 / AdminLTE:** Diseño responsive y panel de administración.
* **Jinja2:** Motor de renderizado de plantillas.

### Base de Datos
* **MariaDB / MySQL:** Almacenamiento relacional para control de acceso (RBAC) y auditoría de despliegues.

---

## Material Multimedia y Entregas (Checkpoints)

* **Checkpoint 1 (Revisión Inicial):** [Enlace al vídeo explicativo](https://youtu.be/DAk_RvIIrWM) 
* **Documentacion (DRIVE)**[ENLACE DOCUMENTACION](https://docs.google.com/document/d/1da0W1-blvOcRLr9vKXel3__spJxI8hNTmVWjxqUPbpA/edit?usp=drive_link)
* **Checkpoint 2 (Revisión 2):** [Enlace al video de checkpoint 2](https://youtu.be/g5xAuYVIswY)
---

## Estructura del Repositorio

```text
/opt/autoservicio/
├── venv/                 
├── .env                  
├── app.py                
├── database.py           
├── proxmox_utils.py      
├── ssh_utils.py          
├── templates/                  
└── static/              
    ├── css/             
    └── img/
