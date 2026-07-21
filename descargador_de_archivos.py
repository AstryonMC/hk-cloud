import requests
import os
from urllib.parse import urlparse, unquote

# Nueva URL solicitada para realizar la descarga
url = "https://manus.im/sandbox/wakeup?url=https%3A%2F%2F5000-iujip7qgqoag7da9owjm8-b2c4f906.us2.manus.computer%2Fdownload"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers, stream=True)
response.raise_for_status()

# Intentar obtener el nombre del archivo desde el header Content-Disposition
filename = None
cd = response.headers.get("Content-Disposition", "")
if "filename=" in cd:
    filename = cd.split("filename=")[-1].strip().strip('"')

# Si no hay header, usar el path de la URL o asignar un nombre predeterminado
if not filename:
    path = urlparse(url).path
    filename = unquote(os.path.basename(path))
    # Si el nombre obtenido es genérico o vacío (como 'wakeup'), le damos un nombre alternativo
    if not filename or filename == "wakeup":
        filename = "archivo_descargado"

with open(filename, "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

print(f"✅ Descargado como: {filename}")
print(f"   Tamaño: {os.path.getsize(filename) / 1024:.1f} KB")