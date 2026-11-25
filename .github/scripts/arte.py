"""Genera las imágenes fijas del perfil (portada, tarjetas de proyecto y foto).

No corre en GitHub Actions: se ejecuta a mano cuando cambia un proyecto.

    python .github/scripts/arte.py <carpeta-con-las-pinturas>

La carpeta debe tener orrery.jpg, vanitas.jpg, bookworm.jpg, libros.jpg y
panteon.jpg (ver CREDITOS.md). Necesita Pillow.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageFilter, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estilo import FUENTES, TEMAS  # noqa: E402

PINTURAS = Path(sys.argv[1])
SALIDA = Path("art")
S = 2  # se dibuja al doble para que se vea nítido en pantallas de alta densidad

PROYECTOS = [
    {
        "archivo": "academic-search-rag", "pintura": "bookworm", "centro": (0.5, 0.33), "lado": 0.42,
        "titulo": "Academic Search RAG",
        "texto": "API grupal que consulta las mallas curriculares de la UNMSM y cita sus fuentes.",
        "chips": ["Python", "FastAPI", "RAG"],
    },
    {
        "archivo": "gestion-pedidos", "pintura": "panteon", "centro": (0.47, 0.42), "lado": 0.62,
        "titulo": "Gestión de Pedidos", "estado": "En desarrollo",
        "texto": "Registro y consulta de pedidos para un estudio de arquitectura.",
        "chips": ["Web", "PostgreSQL"],
    },
    {
        "archivo": "claude-plan-limits", "pintura": "vanitas", "centro": (0.82, 0.5), "lado": 0.66,
        "titulo": "Claude Plan Limits",
        "texto": "Cuánto del plan has usado, cuándo se reinicia y cuánto costaría la sesión.",
        "chips": ["Claude Code", "TypeScript"],
    },
    {
        "archivo": "claude-chat-notes", "pintura": "libros", "centro": (0.7, 0.45), "lado": 0.8,
        "titulo": "Claude Chat Notes",
        "texto": "Guarda fragmentos de las respuestas de Claude como notas ordenadas por tema.",
        "chips": ["Claude Code", "TypeScript"],
    },
]


def letra(size, peso=400, cursiva=False):
    archivo = "EBGaramond-Italic[wght].ttf" if cursiva else "EBGaramond[wght].ttf"
    f = ImageFont.truetype(str(FUENTES / archivo), int(size * S))
    f.set_variation_by_axes([peso])
    return f


def recorte_cuadrado(img, centro, lado):
    """lado es una fracción del lado menor de la pintura."""
    w, h = img.size
    l = int(min(w, h) * lado)
    cx, cy = int(w * centro[0]), int(h * centro[1])
    x0 = min(max(cx - l // 2, 0), w - l)
    y0 = min(max(cy - l // 2, 0), h - l)
    return img.crop((x0, y0, x0 + l, y0 + l))


def panel(w, h, t):
    # Soft ambient tint, fading to transparent at all four edges.
    img = Image.new("RGBA", (w * S, h * S), t["fondo"])
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((18 * S, 18 * S, (w - 18) * S, (h - 18) * S),
                                      radius=36 * S, fill=220)
    m = m.filter(ImageFilter.GaussianBlur(16 * S))
    img.putalpha(m)
    return img, ImageDraw.Draw(img)


def texto_partido(d, texto, fuente, ancho_max):
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if actual and d.textlength(prueba, font=fuente) > ancho_max:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    return lineas + ([actual] if actual else [])


def espaciado(d, xy, texto, fuente, color, extra):
    x, y = xy
    for ch in texto:
        d.text((x, y), ch, font=fuente, fill=color, anchor="ls")
        x += d.textlength(ch, font=fuente) + extra


def portada(tema):
    t = TEMAS[tema]
    W, H = 830, 260
    img, d = panel(W, H, t)
    # Pintura a la derecha, fundida con el panel hacia la izquierda.
    orrery = Image.open(PINTURAS / "orrery.jpg").convert("RGB")
    ow, oh = orrery.size
    pw, ph = int(W * 0.6) * S, (H - 4) * S
    cw = int(ow * 0.88)
    ch = int(cw * ph / pw)
    y0 = int(oh * 0.06)
    pintura = orrery.crop((int(ow * 0.1), y0, int(ow * 0.1) + cw, y0 + ch)).resize((pw, ph), Image.LANCZOS)
    pintura = ImageEnhance.Contrast(pintura).enhance(1.12)
    mascara = Image.new("L", (pw, ph), 255)
    md = ImageDraw.Draw(mascara)
    fundido = int(pw * 0.38)
    for x in range(fundido):
        md.line([(x, 0), (x, ph)], fill=int(255 * (x / fundido) ** 1.6))
    redondeo = Image.new("L", img.size, 0)
    ImageDraw.Draw(redondeo).rounded_rectangle((2 * S, 2 * S, W * S - 2 * S, H * S - 2 * S), radius=5 * S, fill=255)
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    capa.paste(pintura, (W * S - pw - 2 * S, 2 * S), mascara)
    capa.putalpha(Image.composite(capa.getchannel("A"), Image.new("L", img.size, 0), redondeo))
    img = Image.alpha_composite(img, capa)
    d = ImageDraw.Draw(img)
    # Texto
    espaciado(d, (44 * S, 78 * S), "GITHUB  ·  MARK-QUISPE", letra(13, 600), t["oro"], 3 * S)
    d.text((40 * S, 146 * S), "Mark Quispe", font=letra(64, 500), fill=t["titulo"], anchor="ls")
    d.rectangle((44 * S, 164 * S, 104 * S, 166 * S), fill=t["acento"])
    d.text((44 * S, 200 * S), "Computación Científica · UNMSM", font=letra(24, 400, True),
           fill=t["texto"], anchor="ls")
    d.text((44 * S, 228 * S), "Lima, Perú", font=letra(16, 400, True), fill=t["suave"], anchor="ls")
    return img


def tarjeta(p, tema):
    t = TEMAS[tema]
    W, H = 560, 220
    img, d = panel(W, H, t)
    pintura = Image.open(PINTURAS / f'{p["pintura"]}.jpg').convert("RGB")
    miniatura = recorte_cuadrado(pintura, p["centro"], p["lado"]).resize((172 * S, 172 * S), Image.LANCZOS)
    # A softly blurred echo of the painting ties the vignette and text together.
    ambiente = miniatura.resize(img.size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(45*S))
    ambiente = ImageEnhance.Color(ambiente).enhance(0.45).convert("RGBA")
    ambiente.putalpha(img.getchannel("A").point(lambda a: int(a * 0.10)))
    img = Image.alpha_composite(img, ambiente)
    # Blend the painted vignette into the ambient panel, rather than framing it.
    alpha = Image.new("L", miniatura.size, 0)
    ImageDraw.Draw(alpha).rounded_rectangle((12*S, 12*S, 160*S, 160*S), radius=20*S, fill=255)
    alpha = alpha.filter(ImageFilter.GaussianBlur(11*S))
    miniatura = ImageEnhance.Color(miniatura).enhance(0.78)
    miniatura = miniatura.convert("RGBA")
    miniatura.putalpha(alpha)
    img.alpha_composite(miniatura, (24*S, 24*S))
    d = ImageDraw.Draw(img)
    x = 220
    titulo = letra(25, 600)
    d.text((x * S, 58 * S), p["titulo"], font=titulo, fill=t["titulo"], anchor="ls")
    if p.get("estado"):
        fx = x * S + d.textlength(p["titulo"], font=titulo) + 12 * S
        f = letra(12.5, 500)
        ancho = d.textlength(p["estado"], font=f) + 16 * S
        d.rounded_rectangle((fx, 40 * S, fx + ancho, 60 * S), radius=8 * S, fill=t["chip"])
        d.text((fx + 8 * S, 54.5 * S), p["estado"], font=f, fill=t["acento"], anchor="ls")
    # Icono de enlace externo
    ix, iy = W - 40, 26
    d.rectangle((ix * S, (iy + 4) * S, (ix + 12) * S, (iy + 16) * S), outline=t["oro"], width=int(1.3 * S))
    d.rectangle(((ix + 7) * S, (iy) * S, (ix + 17) * S, (iy + 9) * S), fill=t["fondo"])
    d.line(((ix + 6) * S, (iy + 10) * S, (ix + 16) * S, iy * S), fill=t["oro"], width=int(1.3 * S))
    d.line(((ix + 10) * S, iy * S, (ix + 16) * S, iy * S), fill=t["oro"], width=int(1.3 * S))
    d.line(((ix + 16) * S, iy * S, (ix + 16) * S, (iy + 6) * S), fill=t["oro"], width=int(1.3 * S))
    # Descripción
    f = letra(16.5)
    for i, linea in enumerate(texto_partido(d, p["texto"], f, (W - x - 26) * S)[:3]):
        d.text((x * S, (92 + i * 22) * S), linea, font=f, fill=t["texto"], anchor="ls")
    # Etiquetas
    cx, f = x, letra(13.5)
    for chip in p["chips"]:
        ancho = d.textlength(chip, font=f) / S + 22
        d.rounded_rectangle((cx * S, 166 * S, (cx + ancho) * S, 192 * S), radius=13 * S,
                            fill=t["chip"])
        d.text(((cx + 11) * S, 184 * S), chip, font=f, fill=t["texto"], anchor="ls")
        cx += ancho + 8
    return img


def foto():
    vanitas = Image.open(PINTURAS / "vanitas.jpg").convert("RGB")
    return recorte_cuadrado(vanitas, (0.49, 0.53), 0.86).resize((1040, 1040), Image.LANCZOS)


SALIDA.mkdir(exist_ok=True)
for tema in TEMAS:
    portada(tema).save(SALIDA / f"portada-{tema}.png", optimize=True)
    for p in PROYECTOS:
        tarjeta(p, tema).save(SALIDA / f'{p["archivo"]}-{tema}.png', optimize=True)
foto().save(SALIDA / "foto-perfil.jpg", quality=92)
print("Listo:", sorted(x.name for x in SALIDA.iterdir()))
