"""Cifra, firma y envía un archivo a Linux por SFTP.   Uso: python sender.py archivo.pdf"""
import base64
import configparser
import hashlib
import io
import sys
from getpass import getpass
from pathlib import Path

import paramiko

from common import cargar_privada, cargar_publica, cifrar, get_logger, sha256

log = get_logger("sender")


class HuellaFija(paramiko.MissingHostKeyPolicy):
    """Acepta el servidor solo si su huella coincide con la de config.ini."""
    def __init__(self, esperada):
        self.esperada = esperada

    def missing_host_key(self, client, hostname, key):
        huella = "SHA256:" + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
        if huella != self.esperada:
            log.error("IoC: huella del servidor no coincide (%s), posible suplantación", huella)
            raise paramiko.SSHException("Huella del servidor no coincide")


def conectar(cfg):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(HuellaFija(cfg["fingerprint"]))
    ssh.connect(cfg["host"], int(cfg["port"]), cfg["user"],
                password=getpass(f"Contraseña de {cfg['user']}@{cfg['host']}: "), timeout=10)
    return ssh


def main():
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_file():
        sys.exit(__doc__)
    ruta = Path(sys.argv[1])
    cfg = configparser.ConfigParser()
    cfg.read(Path(__file__).parent / "config.ini")
    cfg = cfg["servidor"]

    datos = ruta.read_bytes()
    log.info("Archivo %s, SHA-256 original: %s", ruta.name, sha256(datos))

    enc, key, sig = cifrar(datos, cargar_publica("receiver_public.pem"),
                           cargar_privada("sender_private.pem"))
    log.info("Cifrado AES-256-GCM y firmado Ed25519")

    ssh = conectar(cfg)
    sftp = ssh.open_sftp()
    try:
        sftp.mkdir(cfg["destino"])
    except OSError:
        pass  # ya existe
    # La firma va al final: el receptor la usa como señal de "paquete completo"
    for ext, contenido in (("enc", enc), ("key", key), ("sig", sig)):
        sftp.putfo(io.BytesIO(contenido), f"{cfg['destino']}/{ruta.name}.{ext}")
    ssh.close()
    log.info("Enviado a %s:%s/%s.{enc,key,sig}", cfg["host"], cfg["destino"], ruta.name)


if __name__ == "__main__":
    main()
