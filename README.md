# Secure SFTP Sender

Envía un archivo de **Windows** a **Linux en WSL** protegiendo su confidencialidad e integridad:

| Mecanismo | Uso |
|---|---|
| AES-256-GCM | Cifra el archivo (y detecta alteraciones) |
| RSA-3072 (OAEP) | Protege la llave AES: solo el receptor puede abrirla |
| Ed25519 | Firma el paquete: prueba quién lo envió y que no cambió |
| SHA-256 | Huella del archivo, registrada al enviar y al recibir |
| SSH/SFTP (puerto 22) | Canal de transporte, con huella del servidor fijada |
| Logs + IoC | `sender.log` y `receiver.log` registran firmas inválidas, huella falsa, etc. |

```
Windows: sender.py  --cifra+firma-->  SFTP :22  -->  WSL: receiver.py  --verifica+descifra-->
```

Cada llave privada se genera y se queda en su propio equipo; solo se intercambian las públicas.

---

## Parte 1. Configurar el receptor (WSL)

> **Dónde:** terminal de WSL.

Abre la terminal de tu distribución WSL (Ubuntu/Debian).

**1.1 Instalar lo necesario**
```bash
sudo apt update && sudo apt install -y openssh-server python3-pip python3-venv git
```

**1.2 Puerto SSH**
Se usa el puerto **22** (el predeterminado), no hay que cambiar nada. En Ubuntu 24.04 el puerto lo
define `ssh.socket` y editar `sshd_config` no lo cambia, por eso no se usa otro puerto.
Si Windows también tuviera un servidor SSH propio en el 22, deténlo para evitar conflicto.

**1.3 Arrancar el servicio SSH (único servicio requerido)**
```bash
sudo service ssh start
sudo service ssh status
```
WSL no lo arranca solo: repite `sudo service ssh start` cada vez que reinicies WSL.
No necesitas `ufw` ni abrir puertos.

**1.4 Obtener el proyecto y las dependencias**
```bash
git clone https://github.com/nicolas-170/secure-sftp-sender secure-sftp-sender
cd secure-sftp-sender
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**1.5 Generar las llaves del receptor**
```bash
python3 genkeys.py receiver
```
Elige una passphrase. Se crean en `keys/`:
`receiver_private.pem` (secreta, no sale de WSL) y `receiver_public.pem`.

**1.6 Anotar los valores de conexión**
```bash
whoami                                                  # usuario
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub        # huella: SHA256:xxxx...
```

| Valor | Ejemplo |
|---|---|
| Host | `127.0.0.1` |
| Puerto | `22` |
| Usuario | el de `whoami` |
| Huella del servidor | `SHA256:AbC...` |
| Contraseña | la de tu usuario WSL (se pide al enviar) |

> Windows llega a WSL por `127.0.0.1` gracias al reenvío de localhost de WSL2 (activo por defecto).
> Si no conecta, usa la IP que muestra `ip a` dentro de WSL (cambia al reiniciar).

**Fin de la Parte 1.** Deja la terminal de WSL abierta (SSH corriendo) y **pasa a Windows**:
abre PowerShell y sigue con la Parte 2.

---

## Parte 2. Configurar el emisor (Windows)

> **Dónde:** PowerShell en Windows (no en WSL).

PowerShell, con Python 3.9+ instalado (marca *Add to PATH*).

**2.1 Dependencias**
```powershell
git clone https://github.com/nicolas-170/secure-sftp-sender.git
cd secure-sftp-sender   # si ya estás dentro de la carpeta del proyecto, omite el clone y el cd
python -m venv $HOME\venv-sftp
& $HOME\venv-sftp\Scripts\Activate.ps1
pip install -r requirements.txt
```
El entorno virtual se crea en `$HOME\venv-sftp` (ruta corta) porque si el proyecto está en una
carpeta con ruta muy larga, `python -m venv .venv` falla con `ensurepip ... exit status 1`.
Si PowerShell bloquea el `Activate.ps1`, ejecuta antes (solo afecta a esa ventana):
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

**2.2 Generar las llaves del emisor**
```powershell
python genkeys.py sender
```
Crea `keys\sender_private.pem` (secreta) y `keys\sender_public.pem`.

**2.3 Revisar `config.ini`**: ya trae host `127.0.0.1`, puerto `22`, usuario `nicolas` y la huella de este WSL. Si reinstalas SSH o usas otro WSL, la huella cambia: repite el paso 1.6 y actualízala.

**2.4 Probar la conexión**
```powershell
Test-NetConnection 127.0.0.1 -Port 22
```
Debe mostrar `TcpTestSucceeded : True`.

**Fin de la Parte 2.** Sigues en PowerShell (Windows): ahora intercambias las llaves públicas.

---

## Parte 3. Intercambiar las llaves públicas (solo las `_public.pem`)

> **Dónde:** PowerShell en Windows, dentro de la carpeta del proyecto.

Desde Windows, cambiando `USUARIO` por el de `whoami` (pide la contraseña de WSL):
```powershell
scp -P 22 keys\sender_public.pem USUARIO@127.0.0.1:secure-sftp-sender/keys/
scp -P 22 USUARIO@127.0.0.1:secure-sftp-sender/keys/receiver_public.pem keys\
```
Nunca copies los `_private.pem`.

**Fin de la Parte 3.** Ya están las dos llaves públicas en ambos lados. Ahora se envía desde Windows y se recibe en WSL.

---

## Parte 4. Enviar y recibir

> **Dónde:** el paso 4.1 en PowerShell (Windows); los pasos 4.2 y 4.3 en la terminal de WSL.

**4.1 Enviar (Windows)**
```powershell
python sender.py "C:\ruta\documento.pdf"
```
Pide la passphrase de `sender_private.pem` y la contraseña SSH. Sube a WSL
`documento.pdf.enc`, `.key` y `.sig` a la carpeta `~/recibidos`.

**4.2 Recibir (WSL)**
```bash
cd ~/secure-sftp-sender && source .venv/bin/activate
python3 receiver.py
```
Verifica la firma, descifra y deja el archivo en `~/recibidos/descifrados/`.

**4.3 Comprobar integridad**
Compara el SHA-256 de `sender.log` (Windows) con el de `receiver.log` (WSL): deben ser idénticos.
```bash
sha256sum ~/recibidos/descifrados/documento.pdf
```

---

## Prueba de los IoC (opcional)
Altera un `.enc` en WSL (`echo x >> ~/recibidos/documento.pdf.enc`) y ejecuta `receiver.py`:
`receiver.log` registrará `IoC: firma inválida` y el archivo será rechazado.

## Archivos
| Archivo | Función |
|---|---|
| `common.py` | Cifrado, firma, hash y logs |
| `genkeys.py` | Genera llaves por rol |
| `sender.py` | Cifra, firma y envía (Windows) |
| `receiver.py` | Verifica y descifra (WSL) |
| `config.ini` | Valores de conexión |

## Errores comunes
| Error | Causa |
|---|---|
| `Connection refused` / `timed out` | SSH no está corriendo (`sudo service ssh start`). Comprueba con `sudo ss -ltn` en WSL que aparezca el puerto 22 |
| `Huella del servidor no coincide` | `fingerprint` mal copiada o servidor distinto |
| `Authentication failed` | Usuario o contraseña incorrectos |
| `FileNotFoundError ... public.pem` | Falta el paso 3 |
