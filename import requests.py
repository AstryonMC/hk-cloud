import os
import sys
from urllib.parse import urlparse, unquote

import requests

url = "poner link de descarga"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

TIMEOUT = 30


def resolve_filename(response, url):
    cd = response.headers.get("Content-Disposition", "")
    if "filename=" in cd:
        candidate = cd.split("filename=")[-1].strip().strip('"')
        # Content-Disposition is attacker-controlled: keep only the base name
        # so it cannot escape the working directory.
        candidate = os.path.basename(unquote(candidate)).strip()
        if candidate not in ("", ".", ".."):
            return candidate

    path = urlparse(url).path
    candidate = os.path.basename(unquote(path)).strip()
    if candidate in ("", ".", ".."):
        return "archivo_descargado"
    return candidate


def download(url, headers):
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(f"❌ Error al descargar {url}: {exc}")

    with response:
        filename = resolve_filename(response, url)
        try:
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except (OSError, requests.RequestException) as exc:
            # A partial file is worse than no file: it looks like a success.
            try:
                os.remove(filename)
            except OSError as cleanup_exc:
                print(
                    f"⚠️  No se pudo borrar el archivo parcial {filename}: {cleanup_exc}",
                    file=sys.stderr,
                )
            raise SystemExit(f"❌ Error al guardar {filename}: {exc}")

    return filename


def main():
    filename = download(url, headers)
    print(f"✅ Descargado como: {filename}")
    try:
        size_kb = os.path.getsize(filename) / 1024
    except OSError as exc:
        print(f"⚠️  No se pudo leer el tamaño de {filename}: {exc}", file=sys.stderr)
    else:
        print(f"   Tamaño: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
