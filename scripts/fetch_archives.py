"""Rellena `url_archivo` con una copia permanente de cada fuente.

Motivo: la trazabilidad del dataset depende de URLs de terceros que se
reorganizan, se despublican o bloquean por región. Una copia archivada convierte
cada cita en algo verificable dentro de diez años y desde cualquier red.

Busca en el índice CDX de Internet Archive el snapshot con código 200 más
cercano *posterior* a la fecha del incidente — el que refleja la página tal como
era cuando se citó — y cae al más reciente si no hay ninguno.

    .venv/bin/python scripts/fetch_archives.py           # solo informa
    .venv/bin/python scripts/fetch_archives.py --write   # escribe el CSV
"""

from __future__ import annotations

import csv
import subprocess
import sys
import time
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "data" / "incidents.csv"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = "Mozilla/5.0"


def snapshots(url: str) -> list[tuple[str, str]]:
    """[(timestamp, original)] con código 200, en orden cronológico."""
    consulta = (
        f"{CDX}?url={url}&output=text&fl=timestamp,original,statuscode"
        "&filter=statuscode:200&collapse=digest&limit=200"
    )
    salida = subprocess.run(
        ["curl", "-s", "-A", UA, "--max-time", "60", consulta],
        capture_output=True, text=True,
    ).stdout
    filas = []
    for linea in salida.splitlines():
        partes = linea.split()
        if len(partes) >= 2 and partes[0].isdigit():
            filas.append((partes[0], partes[1]))
    return sorted(filas)


def elegir(filas: list[tuple[str, str]], fecha: str) -> str:
    """El primer snapshot posterior al incidente; si no hay, el más reciente."""
    if not filas:
        return ""
    corte = fecha.replace("-", "")
    posteriores = [f for f in filas if f[0][:8] >= corte]
    ts, original = (posteriores or filas[-1:])[0]
    return f"https://web.archive.org/web/{ts}/{original}"


def main() -> int:
    escribir = "--write" in sys.argv
    filas = list(csv.DictReader(CSV.open(encoding="utf-8")))
    campos = list(filas[0].keys())
    if "url_archivo" not in campos:
        campos.append("url_archivo")

    sin_copia = []
    for fila in filas:
        if fila.get("url_archivo"):
            print(f"··  {fila['id']} ya tenía copia", flush=True)
            continue
        elegido = elegir(snapshots(fila["url"]), fila["fecha"])
        fila["url_archivo"] = elegido
        print(f"{'ok ' if elegido else 'SIN'} {fila['id']} {elegido[:78]}", flush=True)
        if not elegido:
            sin_copia.append(fila["id"])
        time.sleep(1.5)  # el índice CDX limita por IP

    if escribir:
        with CSV.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=campos)
            w.writeheader()
            w.writerows(filas)
        print(f"\nescrito {CSV}")

    print(f"\n{len(filas) - len(sin_copia)}/{len(filas)} con copia archivada")
    if sin_copia:
        print("sin snapshot: " + ", ".join(sin_copia))
    return 0


if __name__ == "__main__":
    sys.exit(main())
