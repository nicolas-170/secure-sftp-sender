"""Verifica la firma y descifra los paquetes recibidos.   Uso: python3 receiver.py [carpeta]"""
import sys
from pathlib import Path

from common import InvalidSignature, InvalidTag, cargar_privada, cargar_publica, descifrar, get_logger, sha256

log = get_logger("receiver")


def main():
    entrada = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "recibidos")
    salida = entrada / "descifrados"
    salida.mkdir(exist_ok=True)
    paquetes = sorted(entrada.glob("*.sig"))
    if not paquetes:
        sys.exit(f"No hay paquetes en {entrada}")

    pub_firma = cargar_publica("sender_public.pem")
    priv_rsa = cargar_privada("receiver_private.pem")

    for sig in paquetes:
        nombre = sig.stem
        try:
            datos = descifrar((entrada / f"{nombre}.enc").read_bytes(),
                              (entrada / f"{nombre}.key").read_bytes(),
                              sig.read_bytes(), pub_firma, priv_rsa)
        except InvalidSignature:
            log.error("IoC: firma inválida en %s (origen no autorizado o archivo alterado)", nombre)
            continue
        except InvalidTag:
            log.error("IoC: fallo de integridad al descifrar %s", nombre)
            continue
        (salida / nombre).write_bytes(datos)
        log.info("OK %s, firma válida. SHA-256 recibido: %s", nombre, sha256(datos))


if __name__ == "__main__":
    main()
