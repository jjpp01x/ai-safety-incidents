"""Comprueba que las 23 fuentes del dataset siguen siendo verificables.

    .venv/bin/python scripts/check_links.py

Un comprobador ingenuo deja sin verificar todo lo que hay detrás de un muro
anti-bot —Reuters, NYT, Bloomberg— y llama "roto" a lo que solo está bloqueado.
Aquí ninguna fila se queda sin veredicto: cuando el origen no se deja consultar,
se verifica su copia en Internet Archive, que es exactamente para lo que está.

Dos casos merecen trato propio y lo tienen:

- **sec.gov** exige un User-Agent con un contacto entre paréntesis (su política
  de acceso automatizado). Con el UA de navegador devuelve 403. Pon el tuyo en
  `SEC_CONTACT` — el valor por defecto es un marcador de posición, no un correo
  real, y la SEC pide uno real para poder avisarte si tu tráfico les molesta:

      SEC_CONTACT=tu@correo.com .venv/bin/python scripts/check_links.py
- **dewr.gov.au** rechaza el handshake desde fuera de su región. No es link rot:
  Internet Archive conserva snapshots 200, y por ahí se verifica.

Veredictos:

- `vivo`   el origen responde 200.
- `copia`  el origen no se deja consultar (403 anti-bot, bloqueo regional…),
           pero la copia archivada responde 200. La cita es verificable.
- `ROTO`   ni origen ni copia. Único caso que obliga a tocar la fila.

Sale con código distinto de 0 solo si hay algún ROTO.
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "data" / "incidents.csv"

UA_NAVEGADOR = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
# La SEC rechaza los UA de navegador: quiere identificación con contacto.
CONTACTO = os.environ.get("SEC_CONTACT", "contacto@ejemplo.com")
UA_POR_HOST = {"sec.gov": f"ai-safety-incidents/1.0 ({CONTACTO})"}


def agente(url: str) -> str:
    return next((ua for host, ua in UA_POR_HOST.items() if host in url), UA_NAVEGADOR)


def estado(url: str) -> str:
    if not url:
        return "---"
    salida = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-A", agente(url), "-L", "--max-time", "30",
         "-w", "%{http_code}", url],
        capture_output=True, text=True,
    ).stdout.strip()
    return salida or "000"


def veredicto(fila: dict) -> tuple[str, str, str]:
    origen = estado(fila["url"])
    if origen == "200":
        return "vivo", origen, ""
    copia = estado(fila.get("url_archivo", ""))
    return ("copia" if copia == "200" else "ROTO"), origen, copia


def main() -> int:
    filas = list(csv.DictReader(CSV.open(encoding="utf-8")))
    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(veredicto, filas))

    grupos: dict[str, list[str]] = {"vivo": [], "copia": [], "ROTO": []}
    for fila, (marca, origen, copia) in zip(filas, resultados):
        grupos[marca].append(fila["id"])
        detalle = f"origen {origen}" + (f" · copia {copia}" if copia else "")
        print(f"{marca:<5} {fila['id']}  {detalle:<26} {fila['fuente'][:38]}")

    verificadas = len(grupos["vivo"]) + len(grupos["copia"])
    print(
        f"\n{verificadas}/{len(filas)} verificadas — "
        f"{len(grupos['vivo'])} por el origen, {len(grupos['copia'])} por copia archivada"
    )
    if grupos["copia"]:
        print("Verificadas por copia: " + ", ".join(grupos["copia"]))
    if grupos["ROTO"]:
        print("ROTAS — hay que sustituir la fuente: " + ", ".join(grupos["ROTO"]))
    return 1 if grupos["ROTO"] else 0


if __name__ == "__main__":
    sys.exit(main())
