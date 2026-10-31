"""Genera las llaves de cada rol. Cada private key se queda en su equipo.

    python genkeys.py sender     (en Windows)  -> firma Ed25519
    python genkeys.py receiver   (en Linux)    -> cifrado RSA-3072
"""
import sys
from getpass import getpass

from cryptography.hazmat.primitives import serialization as s
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

from common import KEYS

ROLES = {
    "sender": lambda: ed25519.Ed25519PrivateKey.generate(),
    "receiver": lambda: rsa.generate_private_key(65537, 3072),
}

if len(sys.argv) != 2 or sys.argv[1] not in ROLES:
    sys.exit(__doc__)

rol = sys.argv[1]
clave = getpass("Passphrase para proteger la llave privada: ").encode()
priv = ROLES[rol]()
KEYS.mkdir(exist_ok=True)
(KEYS / f"{rol}_private.pem").write_bytes(priv.private_bytes(
    s.Encoding.PEM, s.PrivateFormat.PKCS8, s.BestAvailableEncryption(clave)))
(KEYS / f"{rol}_public.pem").write_bytes(priv.public_key().public_bytes(
    s.Encoding.PEM, s.PublicFormat.SubjectPublicKeyInfo))
print(f"[+] keys/{rol}_private.pem (secreta) y keys/{rol}_public.pem (compartir)")
