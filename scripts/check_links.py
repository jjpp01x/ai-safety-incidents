"""Comprueba que las fuentes del dataset siguen vivas.

Un dataset cuyo valor es la trazabilidad se degrada solo: los medios reorganizan
sus URLs y las entradas de blog se renombran. Esto detecta ese deterioro:

    .venv/bin/python scripts/check_links.py

Salida distinta a 0 si hay algún enlace roto. Los 401/403 no cuentan como rotos:
son muros anti-bot (Reuters, NYT, Bloomberg…) que en un navegador abren bien; se
listan aparte para revisarlos a mano.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "data" / "incidents.csv"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
BLOQUEO_ANTIBOT = {"401", "403", "429"}


def estado(url: str) -> str:
    salida = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-A", UA, "-L", "--max-time", "30", "-w", "%{http_code}", url],
        capture_output=True, text=True,
    ).stdout.strip()
    return salida or "000"


def main() -> int:
    filas = list(csv.DictReader(CSV.open(encoding="utf-8")))
    with ThreadPoolExecutor(max_workers=8) as pool:
        codigos = list(pool.map(estado, (f["url"] for f in filas)))

    rotos, dudosos = [], []
    for fila, codigo in zip(filas, codigos):
        if codigo == "200":
            marca = "ok "
        elif codigo in BLOQUEO_ANTIBOT:
            marca, _ = "bot", dudosos.append((fila, codigo))
        else:
            marca, _ = "ROTO", rotos.append((fila, codigo))
        print(f"{marca} {fila['id']} {codigo} {fila['fuente'][:40]}")

    print(f"\n{len(filas) - len(rotos) - len(dudosos)} ok · "
          f"{len(dudosos)} bloqueados por anti-bot · {len(rotos)} rotos")
    if dudosos:
        print("Anti-bot (verificar en navegador): " + ", ".join(f["id"] for f, _ in dudosos))
    if rotos:
        print("ROTOS: " + ", ".join(f"{f['id']} ({c})" for f, c in rotos))
    return 1 if rotos else 0


if __name__ == "__main__":
    sys.exit(main())
