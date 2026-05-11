import os
from dotenv import load_dotenv
from proxmoxer import ProxmoxAPI
import urllib3
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
def conectar_proxmox():
	token_completo = os.getenv('PROXMOX_TOKEN_ID')
	#Separamos el usuario y el nombre del token con un split en !
	usuario, nombre_token = token_completo.split('!')
	return ProxmoxAPI(os.getenv('PROXMOX_IP'), user=usuario,token_name=nombre_token, token_value=os.getenv('PROXMOX_SECRET'), verify_ssl=False)
def obtener_servicios_activos():
	proxmox = conectar_proxmox()
	servicios = proxmox.nodes('alejandro').lxc.get()
	print(servicios)
	activos = [ct for ct in servicios if ct.get('status') == 'running']
	return activos
