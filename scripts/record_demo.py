"""Graba la demo del dashboard (docs/demo.gif) y las capturas del README.

Levanta la app en un puerto libre, la recorre con Playwright y monta el GIF con
Pillow. Se ejecuta a mano cuando cambia la UI, no en CI:

    .venv/bin/python scripts/record_demo.py

Requisitos: `uv pip install playwright pillow && .venv/bin/playwright install chromium`
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FRAMES = DOCS / "frames"

ANCHO, ALTO = 1440, 900
ANCHO_GIF = 1000
ESPERA_RERUN = 1.4  # Streamlit re-ejecuta el script entero en cada interacción


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def arrancar(puerto: int) -> subprocess.Popen:
    proc = subprocess.Popen(
        [
            str(ROOT / ".venv/bin/streamlit"), "run", str(ROOT / "app.py"),
            "--server.port", str(puerto), "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    for _ in range(60):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", puerto)) == 0:
                time.sleep(2)
                return proc
        time.sleep(0.5)
    proc.kill()
    raise RuntimeError("la app no arrancó")


class Grabadora:
    def __init__(self, page):
        self.page = page
        self.n = 0

    def frame(self, repite: int = 1) -> None:
        """Captura el estado actual; `repite` alarga la pausa en el GIF."""
        self.page.wait_for_timeout(250)
        destino = FRAMES / f"{self.n:03d}.png"
        self.page.screenshot(path=str(destino))
        self.n += 1
        for _ in range(repite - 1):
            shutil.copy(destino, FRAMES / f"{self.n:03d}.png")
            self.n += 1


def recorrido(page, rec: Grabadora) -> None:
    page.wait_for_selector("text=AI Safety Incident Tracker", timeout=30_000)
    page.wait_for_timeout(2500)
    page.screenshot(path=str(DOCS / "01-panorama.png"))
    rec.frame(6)

    # La mitad inferior del panorama (serie temporal y densidad), solo como captura.
    page.mouse.move(700, 500)
    page.mouse.wheel(0, 900)
    page.wait_for_timeout(1800)
    page.screenshot(path=str(DOCS / "07-serie-temporal.png"))
    rec.frame(4)
    page.mouse.wheel(0, -900)
    page.wait_for_timeout(900)
    rec.frame(2)

    # 1. Subir el umbral de severidad.
    slider = page.locator('[data-testid="stSlider"]').nth(1).locator('input[type="range"]')
    slider.first.focus()
    for _ in range(3):
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(int(ESPERA_RERUN * 1000))
        rec.frame(2)
    rec.frame(4)
    page.screenshot(path=str(DOCS / "03-severidad-alta.png"))
    for _ in range(3):
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(int(ESPERA_RERUN * 1000))
    rec.frame(2)

    # 2. Modo oscuro: pasos propios de la misma rampa, no un volteo automático.
    page.goto(f"{page.url.split('?')[0]}?tema=dark", wait_until="networkidle")
    page.wait_for_timeout(3500)
    rec.frame(6)
    page.screenshot(path=str(DOCS / "04-modo-oscuro.png"))
    page.goto(f"{page.url.split('?')[0]}?tema=light", wait_until="networkidle")
    page.wait_for_timeout(3500)
    rec.frame(2)

    # 3. ¿Era previsible?: el eje que convierte el recuento en lectura de riesgo.
    page.get_by_role("tab", name="¿Era previsible?").click()
    page.wait_for_timeout(1500)
    rec.frame(6)
    page.screenshot(path=str(DOCS / "08-previsible.png"))
    page.mouse.wheel(0, 600)
    page.wait_for_timeout(700)
    rec.frame(4)
    page.mouse.wheel(0, -600)
    page.wait_for_timeout(600)

    # 4. Caso en profundidad.
    page.get_by_role("tab", name="Caso en profundidad").click()
    page.wait_for_timeout(1200)
    rec.frame(5)
    page.screenshot(path=str(DOCS / "05-caso.png"))
    for _ in range(3):
        page.mouse.wheel(0, 700)
        page.wait_for_timeout(500)
        rec.frame(2)

    # 5. Dataset: la vista de tabla, obligatoria cuando el color no basta.
    page.mouse.wheel(0, -3000)
    page.wait_for_timeout(600)
    page.get_by_role("tab", name="Dataset").click()
    page.wait_for_timeout(1500)
    rec.frame(4)
    page.mouse.wheel(0, 500)
    page.wait_for_timeout(800)
    rec.frame(6)
    page.screenshot(path=str(DOCS / "06-dataset.png"))

    page.mouse.wheel(0, -3000)
    page.get_by_role("tab", name="Panorama").click()
    page.wait_for_timeout(1200)
    rec.frame(3)

    # 6. Aislar los fallos de seguridad: el color de cada tipo no se mueve al filtrar.
    for etiqueta in ("Contención", "Sesgo", "Alucinación"):
        chip = page.locator(
            f'span[data-baseweb="tag"]:has-text("{etiqueta}") span[role="presentation"]'
        )
        if chip.count():
            chip.first.click()
            page.wait_for_timeout(int(ESPERA_RERUN * 1000))
            rec.frame(2)
    rec.frame(8)
    page.screenshot(path=str(DOCS / "02-filtro-seguridad.png"))


def montar_gif() -> Path:
    imagenes = sorted(FRAMES.glob("*.png"))
    if not imagenes:
        raise RuntimeError("no hay frames")
    marcos = []
    for p in imagenes:
        im = Image.open(p).convert("RGB")
        im = im.resize((ANCHO_GIF, round(im.height * ANCHO_GIF / im.width)), Image.LANCZOS)
        marcos.append(im.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG))
    salida = DOCS / "demo.gif"
    marcos[0].save(
        salida, save_all=True, append_images=marcos[1:],
        duration=320, loop=0, optimize=True, disposal=2,
    )
    return salida


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    shutil.rmtree(FRAMES, ignore_errors=True)
    FRAMES.mkdir(parents=True)

    puerto = puerto_libre()
    proc = arrancar(puerto)
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            page = navegador.new_page(viewport={"width": ANCHO, "height": ALTO})
            page.goto(f"http://127.0.0.1:{puerto}", wait_until="networkidle")
            rec = Grabadora(page)
            recorrido(page, rec)
            navegador.close()
    finally:
        proc.terminate()
        proc.wait(timeout=10)

    gif = montar_gif()
    print(f"{gif}  ({gif.stat().st_size / 1e6:.1f} MB, {len(list(FRAMES.glob('*.png')))} frames)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
