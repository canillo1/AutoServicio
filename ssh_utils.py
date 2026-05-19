import paramiko
import time
import logging

# Configuracion basica del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class SSHManager:
    def __init__(self, ip, username="root", password=None):
        self.ip = ip
        self.username = username
        self.password = password
        self.port = 22
        self.timeout = 10

    def conectar_y_ejecutar(self, comandos):
        """
        Ejecuta comandos simples sin transferir archivos (ideal para añadir registros al DNS)
        """
        cliente = paramiko.SSHClient()
        cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conectado = False
        intentos = 6

        for intento in range(intentos):
            try:
                cliente.connect(hostname=self.ip, port=self.port, username=self.username, password=self.password, timeout=self.timeout)
                conectado = True
                break
            except Exception as e:
                logger.warning(f"Error en la conexion: {str(e)}")
                if intento < intentos - 1:
                    time.sleep(7)
        
        if not conectado:
            return False, "Error en ssh"

        exito_total = True
        resultados = []
        try:
            for comando in comandos:
                logger.info(f"Ejecutando: {comando}")
                stdin, stdout, stderr = cliente.exec_command(comando)
                exit_status = stdout.channel.recv_exit_status()
                error_txt = stderr.read().decode("utf-8").strip()
                
                if exit_status != 0:
                    exito_total = False
                    logger.error(f"Error en el comando: {error_txt}")
                    resultados.append(f"Error en {comando}: {error_txt}")
                    break
                else:
                    resultados.append(f"Exito: {comando}")
            return exito_total, resultados
        finally:
            cliente.close()

    def inyectar_configuracion(self, archivos, comandos_post):
        """
        Conecta por SFTP, sube los archivos de configuracion y ejecuta comandos de reinicio.
        'archivos' debe ser una lista de diccionarios con 'ruta' y 'texto'.
        """
        cliente = paramiko.SSHClient()
        cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        intentos = 3
        conectado = False
        
        for intento in range(intentos):
            try:
                logger.info(f"Conectando a {self.ip} Intento numero {intento+1}/{intentos}")
                cliente.connect(
                    hostname=self.ip,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=self.timeout
                )
                conectado = True
                break
            except Exception as e:
                logger.warning(f"Error en la conexion: {str(e)}")
                if intento < intentos - 1:
                    time.sleep(5)
                    
        if not conectado:
            logger.error(f"No es posible conectar a {self.ip}")
            return False, "Error en ssh"
            
        exito_total = True
        resultados = []
        
        try:
            sftp = cliente.open_sftp()
            # Bucle para subir todos los archivos necesarios (1 para DHCP, 3 para DNS)
            for archivo in archivos:
                ruta_destino = archivo['ruta']
                contenido = archivo['texto']
                logger.info(f"Escribiendo configuracion en {ruta_destino}")
                
                with sftp.file(ruta_destino, "w") as f:
                    f.write(contenido)
                    
            sftp.close()
            logger.info("Archivos escritos con exito.")
            
            for comando in comandos_post:
                logger.info(f"Ejecutando: {comando}")
                stdin, stdout, stderr = cliente.exec_command(comando)
                exit_status = stdout.channel.recv_exit_status()
                error_txt = stderr.read().decode("utf-8").strip()
                
                if exit_status != 0:
                    exito_total = False
                    logger.error(f"Error en el comando: {error_txt}")
                    resultados.append(f"Error en {comando}: {error_txt}")
                    break
                else:
                    resultados.append(f"Exito: {comando}")
                    
            return exito_total, resultados
            
        except Exception as e:
            logger.error(f"Error en la inyeccion: {str(e)}")
            return False, str(e)
            
        finally:
            cliente.close()
            logger.info(f"Conexion con {self.ip} cerrada.")

    def configurar_dhcp(self, red, mascara, ip_inicio, ip_fin, gateway, dns):
        logger.info("Preparando la inyeccion de DHCP")
        
        texto_config = f"""default-lease-time 600;
max-lease-time 7200;
authoritative;

subnet {red} netmask {mascara} {{
    range {ip_inicio} {ip_fin};
    option routers {gateway};
    option domain-name-servers {dns};
}}
"""
        lista_archivos = [{'ruta': '/etc/dhcp/dhcpd.conf', 'texto': texto_config}]
        comandos = ["systemctl restart isc-dhcp-server"]
        return self.inyectar_configuracion(lista_archivos, comandos)

    def configurar_dns(self, red_permitida, nombre_dominio, ip_dns):
        logger.info(f"Iniciando inyeccion de configuracion DNS para {nombre_dominio}...")

        opciones_globales = f"""acl "trusted" {{
    127.0.0.0/8;
    {red_permitida};
}};
options {{
    directory "/var/cache/bind";
    recursion yes;
    allow-query {{ trusted; }};
    forwarders {{ 8.8.8.8; 1.1.1.1; }};
    forward only;
    dnssec-validation auto;
    listen-on-v6 {{ any; }};
}};
"""
        declaracion_zona = f"""
zone "{nombre_dominio}" {{
    type master;
    file "/var/lib/bind/db.{nombre_dominio}";
}};
"""
        registros_zona = f"""$TTL    604800
@       IN      SOA     ns1.{nombre_dominio}. admin.{nombre_dominio}. (
                              1         ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         604800 )       ; Negative Cache TTL
;
@       IN      NS      ns1.{nombre_dominio}.
ns1     IN      A       {ip_dns}
"""
        lista_archivos = [
            {'ruta': '/etc/bind/named.conf.options', 'texto': opciones_globales},
            {'ruta': '/etc/bind/named.conf.local', 'texto': declaracion_zona},
            {'ruta': f'/var/lib/bind/db.{nombre_dominio}', 'texto': registros_zona}
        ]
        comandos = ["systemctl restart bind9"]
        
        return self.inyectar_configuracion(lista_archivos, comandos)

    def aniadir_registro_dns(self, zona_dominio, nombre_host, tipo_registro, valor_destino, ttl):
        logger.info(f"Añadiendo registro a {zona_dominio}: {nombre_host} -> {valor_destino}")
        registro = f"{nombre_host}    {ttl}    IN    {tipo_registro}    {valor_destino}"
        archivo_zona = f"/var/lib/bind/db.{zona_dominio}"
        comandos = [
            f"echo '{registro}' >> {archivo_zona}",
            "systemctl reload bind9"
        ]
        return self.conectar_y_ejecutar(comandos)

    def eliminar_registro_dns(self, zona_dominio, nombre_host):
        logger.info(f"Eliminando el host {nombre_host} del dominio {zona_dominio}...")
        archivo_zona = f"/var/lib/bind/db.{zona_dominio}"
        comandos = [
            f"sed -i '/^{nombre_host}/d' {archivo_zona}",
            "systemctl reload bind9"
        ]
        return self.conectar_y_ejecutar(comandos)

    def configurar_web(self, contenido_html, servicio_web="apache2"):
        logger.info(f"Iniciando inyeccion de configuracion Web ({servicio_web})...")
        ruta_index = "/var/www/html/index.html"
        lista_archivos = [
            {'ruta': ruta_index, 'texto': contenido_html}
        ]
        comandos = [f"systemctl restart {servicio_web}"]
        return self.inyectar_configuracion(lista_archivos, comandos)
