import os
from dotenv import load_dotenv
from proxmoxer import ProxmoxAPI
import urllib3
import subprocess
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
def conectar_proxmox():
    token_completo = os.getenv('PROXMOX_TOKEN_ID')
    # Separamos el usuario y el nombre del token con un split en !
    usuario, nombre_token = token_completo.split('!')
    return ProxmoxAPI(
        os.getenv('PROXMOX_IP'), 
        user=usuario,
        token_name=nombre_token, 
        token_value=os.getenv('PROXMOX_SECRET'), 
        verify_ssl=False)
def obtener_servicios_activos():
    proxmox = conectar_proxmox()
    servicios = proxmox.nodes('alejandro').lxc.get()
    return servicios
def obtener_id_lxc_libre():
    proxmox = conectar_proxmox()
    try:
        siguiente_id = proxmox.cluster.nextid.get()
        return int(siguiente_id)
    except Exception as e:
        print("La API nextid no responde:", e, "Calculando el ID del lxc manualmente...")
        try:
            servicios = proxmox.nodes('alejandro').lxc.get()
            if len(servicios) == 0:
                return 100
            ids_lxc = [int(ct.get('vmid')) for ct in servicios]
            siguiente_id_manual = max(ids_lxc) + 1 
            return siguiente_id_manual
        except Exception as error_interno:
            raise Exception("No se pudo calcular el ID libre para el lxc", error_interno)
def obtener_ip_libre(ips_registradas):
    ip_base = os.getenv('RED_BASE')
    rango_inicio = int(os.getenv('IP_RANGO_INICIO'))
    rango_fin = int(os.getenv('IP_RANGO_FIN'))
    for i in range(rango_inicio, rango_fin + 1):
        ip_candidata = f"{ip_base}{i}"
        if ip_candidata in ips_registradas:
            continue
        respuesta = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip_candidata],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        if respuesta.returncode != 0:
            return ip_candidata
    raise Exception(f"No quedan direcciones IP libres en el rango {rango_inicio}-{rango_fin}")
