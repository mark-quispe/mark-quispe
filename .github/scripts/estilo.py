"""Paleta y tipografía compartidas por las imágenes del perfil.

El texto de los SVG se convierte en trazos (paths) con la fuente EB Garamond,
así se ve igual en cualquier navegador sin cargar fuentes externas.
"""
from functools import lru_cache
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

FUENTES = Path(__file__).resolve().parent.parent / "fonts"
GLIFOS = {}  # glifos usados en el SVG que se está armando

TEMAS = {
    "dark": {
        "fondo": "#15191e", "borde": "#30363d", "titulo": "#eee4d6", "texto": "#c8c4c1",
        "suave": "#92979e", "acento": "#cc514d", "oro": "#c8ad8f", "chip": "#20252b",
        "vacio": "#21262d", "escala": ["#4a1d1b", "#7a2523", "#a52f2b", "#d0453a"],
    },
    "light": {
        "fondo": "#f3f1ed", "borde": "#d0d7de", "titulo": "#29221f", "texto": "#42464a",
        "suave": "#656d76", "acento": "#a23836", "oro": "#84664d", "chip": "#eaeef2",
        "vacio": "#ebedf0", "escala": ["#e7b3a6", "#cf7a6c", "#b0463e", "#a23836"],
    },
}


class Fuente:
    def __init__(self, archivo, peso):
        self.id = f"{'i' if 'Italic' in archivo else 'r'}{peso}"
        font = instantiateVariableFont(TTFont(FUENTES / archivo), {"wght": peso})
        self.glyphs = font.getGlyphSet()
        self.cmap = font.getBestCmap()
        self.upm = font["head"].unitsPerEm
        self.hmtx = font["hmtx"]

    def _glifo(self, ch):
        return self.cmap.get(ord(ch), ".notdef")

    def ancho(self, texto, size, espaciado=0.0):
        avances = [self.hmtx[self._glifo(ch)][0] * size / self.upm for ch in texto]
        return sum(avances) + espaciado * max(len(texto) - 1, 0)

    def path(self, texto, x, y, size, color, ancla="start", espaciado=0.0):
        """Devuelve el texto como glifos reutilizables; (x, y) es la línea base."""
        escala = size / self.upm
        ancho = self.ancho(texto, size, espaciado)
        if ancla == "end":
            x -= ancho
        elif ancla == "middle":
            x -= ancho / 2
        usos = []
        for ch in texto:
            nombre = self._glifo(ch)
            gid = f"{self.id}-{ord(ch):x}"
            if gid not in GLIFOS:
                pen = SVGPathPen(self.glyphs, ntos=lambda v: str(round(v)))
                self.glyphs[nombre].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))
                GLIFOS[gid] = pen.getCommands()
            if GLIFOS[gid]:
                usos.append(f'<use href="#{gid}" transform="translate({x:.1f} {y:.1f}) scale({escala:.5f})"/>')
            x += self.hmtx[nombre][0] * escala + espaciado
        return f'<g fill="{color}">{"".join(usos)}</g>' if usos else ""

    def partir(self, texto, size, ancho_max):
        """Parte el texto en líneas que caben en ancho_max."""
        lineas, actual = [], ""
        for palabra in texto.split():
            prueba = f"{actual} {palabra}".strip()
            if actual and self.ancho(prueba, size) > ancho_max:
                lineas.append(actual)
                actual = palabra
            else:
                actual = prueba
        if actual:
            lineas.append(actual)
        return lineas


@lru_cache(maxsize=None)
def fuente(peso=400, cursiva=False):
    archivo = "EBGaramond-Italic[wght].ttf" if cursiva else "EBGaramond[wght].ttf"
    return Fuente(archivo, peso)


def marco(ancho, alto, t):
    """Sombra ambiental suave; bordes completamente transparentes."""
    return (
        f'<defs><radialGradient id="ambiente" cx="50%" cy="50%" r="50%">'
        f'<stop offset="0%" stop-color="{t["fondo"]}" stop-opacity="0.85"/>'
        f'<stop offset="55%" stop-color="{t["fondo"]}" stop-opacity="0.55"/>'
        f'<stop offset="100%" stop-color="{t["fondo"]}" stop-opacity="0"/>'
        f'</radialGradient></defs><rect width="{ancho}" height="{alto}" fill="url(#ambiente)"/>'
    )


def svg(ancho, alto, titulo, cuerpo):
    from xml.sax.saxutils import escape
    defs = "".join(f'<path id="{gid}" d="{d}"/>' for gid, d in GLIFOS.items() if d)
    GLIFOS.clear()
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" '
        f'viewBox="0 0 {ancho} {alto}" role="img"><title>{escape(titulo)}</title>'
        f'<defs>{defs}</defs>{cuerpo}</svg>'
    )
