"""Comprueba que las fuentes del dataset siguen siendo verificables.

Un dataset cuyo valor es la trazabilidad se degrada solo: los medios reorganizan
sus URLs, las entradas de blog se renombran y algunos dominios bloquean tráfico
por región. Esto detecta ese deterioro:

    .venv/bin/python scripts/check_links.py

Cuatro veredictos, y conviene no confundirlos:

- `ok`      la fuente responde 200.
- `bot`     401/403/429: muro anti-bot (Reuters, NYT, Bloomberg…). Abre bien en
            un navegador; el script no puede confirmarlo y lo lista aparte.
- `archivo` el origen no responde desde aquí, pero la copia en Internet Archive
            sí. La cita sigue siendo verificable; el enlace vivo, no siempre.
- `ROTO`    ni el origen ni la copia. Es el único caso que exige tocar la fila.

Sale con código distinto de 0 solo si hay algún ROTO.
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
    if not url:
        return "000"
    salida = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-A", UA, "-L", "--max-time", "30",
         "-w", "%{http_code}", url],
        capture_output=True, text=True,
    ).stdout.strip()
    return salida or "000"


def veredicto(fila: dict) -> tuple[str, str]:
    codigo = estado(fila["url"])
    if codigo == "200":
        return "ok ", codigo
    if codigo in BLOQUEO_ANTIBOT:
        return "bot", codigo
    if estado(fila.get("url_archivo", "")) == "200":
        return "archivo", codigo
    return "ROTO", codigo


def main() -> int:
    filas = list(csv.DictReader(CSV.open(encoding="utf-8")))
    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(veredicto, filas))

    grupos: dict[str, list[str]] = {"ok ": [], "bot": [], "archivo": [], "ROTO": []}
    for fila, (marca, codigo) in zip(filas, resultados):
        grupos[marca].append(fila["id"])
        print(f"{marca:<7} {fila['id']} {codigo} {fila['fuente'][:40]}")

    print(
        f"\n{len(grupos['ok '])} vivas · {len(grupos['bot'])} tras muro anti-bot · "
        f"{len(grupos['archivo'])} solo por copia archivada · {len(grupos['ROTO'])} rotas"
    )
    for clave, etiqueta in (
        ("bot", "Anti-bot (verificar en navegador)"),
        ("archivo", "Solo copia archivada"),
        ("ROTO", "ROTAS — hay que sustituir la fuente"),
    ):
        if grupos[clave]:
            print(f"{etiqueta}: {', '.join(grupos[clave])}")
    return 1 if grupos["ROTO"] else 0


if __name__ == "__main__":
    sys.exit(main())
