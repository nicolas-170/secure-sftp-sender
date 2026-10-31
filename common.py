"""Funciones compartidas: cifrado híbrido, firma, hash y registro de eventos."""
import hashlib
import logging
import os
from getpass import getpass
from pathlib import Path

from cryptography.exceptions import InvalidSignature, InvalidTag  # noqa: F401
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEYS = Path(__file__).parent / "keys"
OAEP = padding.OAEP(padding.MGF1(hashes.SHA256()), hashes.SHA256(), None)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_logger(nombre: str) -> logging.Logger:
    log = logging.getLogger(nombre)
    if not log.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        for h in (logging.StreamHandler(), logging.FileHandler(f"{nombre}.log", encoding="utf-8")):
            h.setFormatter(fmt)
            log.addHandler(h)
        log.setLevel(logging.INFO)
    return log


def cargar_publica(nombre: str):
    return serialization.load_pem_public_key((KEYS / nombre).read_bytes())


def cargar_privada(nombre: str):
    clave = getpass(f"Passphrase de {nombre}: ").encode()
    return serialization.load_pem_private_key((KEYS / nombre).read_bytes(), clave)


def cifrar(datos: bytes, pub_rsa, priv_firma):
    """AES-256-GCM para los datos, RSA-OAEP para la llave AES, Ed25519 para la firma."""
    aes_key, nonce = AESGCM.generate_key(256), os.urandom(12)
    enc = nonce + AESGCM(aes_key).encrypt(nonce, datos, None)
    key = pub_rsa.encrypt(aes_key, OAEP)
    return enc, key, priv_firma.sign(enc + key)


def descifrar(enc: bytes, key: bytes, sig: bytes, pub_firma, priv_rsa) -> bytes:
    """Verifica la firma (InvalidSignature) y descifra (InvalidTag si fue alterado)."""
    pub_firma.verify(sig, enc + key)
    aes_key = priv_rsa.decrypt(key, OAEP)
    return AESGCM(aes_key).decrypt(enc[:12], enc[12:], None)
