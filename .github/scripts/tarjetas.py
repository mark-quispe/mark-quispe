"""Genera las imágenes dinámicas del perfil en cards/ (versión clara y oscura).

- stats:      commits, PRs, repos y lenguajes.
- languages:  lenguajes por tamaño del código.
- actividad:  repos públicos con commits recientes y calendario de contribuciones.
- separador y sobre-mi: piezas fijas con el mismo estilo.

Usa GH_TOKEN. Con un token personal del dueño (STATS_TOKEN) también cuenta los
repositorios privados; con el token automático de Actions solo ve los públicos.
Los nombres de repos privados nunca aparecen: solo totales.
"""
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estilo import TEMAS, fuente, marco, svg  # noqa: E402

PROFILE = os.environ["PROFILE"]
TOKEN = os.environ["GH_TOKEN"]
MESES = "ene feb mar abr may jun jul ago sep oct nov dic".split()

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
      commitContributionsByRepository(maxRepositories: 25) {
        contributions { totalCount }
        repository {
          nameWithOwner name pushedAt isPrivate isFork
          primaryLanguage { name }
        }
      }
    }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes {
        isPrivate
        languages(first: 30) { edges { size node { name color } } }
      }
    }
  }
}
"""


def graphql(variables):
    body = json.dumps({"query": QUERY, "variables": variables}).encode()
    request = Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": "Bearer " + TOKEN,
        "Content-Type": "application/json",
    })
    with urlopen(request, timeout=30) as response:
        data = json.load(response)
    if data.get("errors"):
        raise SystemExit(f"Error de la API de GitHub: {data['errors']}")
    return data["data"]["user"]


# --- Datos --------------------------------------------------------------------
repos, after = [], None
while True:
    user = graphql({"login": PROFILE, "after": after})
    page = user["repositories"]
    repos += page["nodes"]
    if not page["pageInfo"]["hasNextPage"]:
        break
    after = page["pageInfo"]["endCursor"]

contrib = user["contributionsCollection"]
alcance = "públicos y privados" if any(r["isPrivate"] for r in repos) else "públicos"

sizes, colors = Counter(), {}
for repo in repos:
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        sizes[name] += edge["size"]
        colors[name] = edge["node"]["color"] or "#8a7d70"
total = sum(sizes.values())
lenguajes = sizes.most_common(5)
if len(sizes) > 5:
    lenguajes.append(("Otros", total - sum(s for _, s in lenguajes)))
    colors["Otros"] = "#8a7d70"

recientes = [
    item for item in contrib["commitContributionsByRepository"]
    if not item["repository"]["isPrivate"] and not item["repository"]["isFork"]
    and item["repository"]["primaryLanguage"]
    and item["repository"]["nameWithOwner"].lower() != f"{PROFILE}/{PROFILE}".lower()
]
recientes.sort(key=lambda item: item["repository"]["pushedAt"], reverse=True)
recientes = recientes[:4]

dias = [d for w in contrib["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
semanas = contrib["contributionCalendar"]["weeks"][-26:]

estadisticas = [
    ("Commits (último año)",
     contrib["totalCommitContributions"] + contrib["restrictedContributionsCount"]),
    ("Pull requests (último año)", contrib["totalPullRequestContributions"]),
    ("Repositorios con commits", contrib["totalRepositoriesWithContributedCommits"]),
    (f"Repositorios {alcance}", len(repos)),
    ("Lenguajes usados", len(sizes)),
]

serif, negrita, cursiva = fuente(400), fuente(600), fuente(400, cursiva=True)


def fecha_corta(iso):
    y, m, d = iso[:10].split("-")
    return f"{int(d)} {MESES[int(m) - 1]}"


def titulo(texto, x, y, t, ancho_linea):
    return (negrita.path(texto, x, y, 21, t["titulo"])
            + f'<rect x="{x}" y="{y + 11}" width="{ancho_linea}" height="1" fill="{t["borde"]}"/>')


def rombo(x, y, r, color):
    return f'<path fill="{color}" d="M{x} {y - r}L{x + r} {y}L{x} {y + r}L{x - r} {y}Z"/>'


# --- Piezas -------------------------------------------------------------------
def tarjeta_stats(t):
    W, H = 400, 200
    filas = []
    for i, (label, value) in enumerate(estadisticas):
        y = 82 + i * 25
        filas.append(rombo(32, y - 5, 3.5, t["oro"]))
        filas.append(serif.path(label, 46, y, 16.5, t["texto"]))
        filas.append(negrita.path(f"{value:,}".replace(",", " "), W - 28, y, 17, t["titulo"], "end"))
    return svg(W, H, "Estadísticas de GitHub",
               marco(W, H, t) + titulo("Estadísticas de GitHub", 26, 40, t, W - 52) + "".join(filas))


def tarjeta_lenguajes(t):
    tonos = {nombre: COLORES_LENGUAJES[i] for i, (nombre, _) in enumerate(lenguajes)}
    W, H = 400, 200
    partes = ['<defs><clipPath id="barra"><rect x="26" y="70" width="348" height="10" rx="5"/></clipPath></defs>'
              '<g clip-path="url(#barra)">']
    x = 26.0
    for nombre, size in lenguajes:
        w = 348 * size / total
        partes.append(f'<rect x="{x:.2f}" y="70" width="{w:.2f}" height="10" fill="{tonos[nombre]}"/>')
        x += w
    partes.append("</g>")
    for i, (nombre, size) in enumerate(lenguajes):
        cx, cy = 26 + (i % 2) * 180, 108 + (i // 2) * 24
        pct = f"{100 * size / total:.1f}".replace(".", ",") + " %"
        partes.append(f'<rect x="{cx}" y="{cy - 10}" width="10" height="10" rx="2" fill="{tonos[nombre]}"/>')
        partes.append(serif.path(nombre, cx + 17, cy, 16, t["texto"]))
        partes.append(serif.path(pct, cx + 160, cy, 15, t["suave"], "end"))
    if not lenguajes:
        partes = [serif.path("Sin lenguajes detectados", 26, 100, 16, t["suave"])]
    partes.append(cursiva.path(f"Por tamaño del código en mis repositorios {alcance}", 26, 186, 12.5, t["suave"]))
    return svg(W, H, "Lenguajes más usados",
               marco(W, H, t) + titulo("Lenguajes más usados", 26, 40, t, W - 52) + "".join(partes))


def tarjeta_actividad(t):
    W, H = 830, 250
    partes = [marco(W, H, t), titulo("Actividad reciente", 28, 42, t, 360)]
    for i, item in enumerate(recientes):
        repo = item["repository"]
        y = 92 + i * 40
        n = item["contributions"]["totalCount"]
        partes.append(rombo(34, y - 5, 3.5, t["acento"]))
        partes.append(serif.path(repo["name"], 48, y, 17.5, t["titulo"]))
        meta = (f'{repo["primaryLanguage"]["name"]} · {n} commit{"s" if n != 1 else ""}'
                f' · {fecha_corta(repo["pushedAt"])}')
        partes.append(cursiva.path(meta, 48, y + 18, 13.5, t["suave"]))
    if not recientes:
        partes.append(cursiva.path("Sin actividad pública reciente", 48, 92, 15, t["suave"]))

    # Separador vertical
    partes.append(f'<rect x="418" y="30" width="1" height="{H - 60}" fill="{t["borde"]}" opacity="0.7"/>')

    # Calendario de las últimas 26 semanas
    x0, y0, celda, paso = 446, 92, 11, 14
    partes.append(titulo("Contribuciones", x0, 42, t, W - x0 - 28))
    maximo = max([d["contributionCount"] for w in semanas for d in w["contributionDays"]] + [1])
    inicios = []  # (columna, mes) donde empieza cada mes
    for c, semana in enumerate(semanas):
        mes = int(semana["contributionDays"][0]["date"][5:7])
        if not inicios or inicios[-1][1] != mes:
            inicios.append((c, mes))
    for i, (c, mes) in enumerate(inicios):
        fin = inicios[i + 1][0] if i + 1 < len(inicios) else len(semanas)
        if fin - c >= 3:  # solo se rotula si el mes ocupa espacio suficiente
            partes.append(serif.path(MESES[mes - 1].capitalize(), x0 + c * paso, y0 - 10, 12.5, t["suave"]))
    for c, semana in enumerate(semanas):
        for dia in semana["contributionDays"]:
            fila = date.fromisoformat(dia["date"]).isoweekday() % 7  # domingo = 0
            n = dia["contributionCount"]
            if n == 0:
                color = t["vacio"]
            else:
                color = t["escala"][min(3, int(4 * n / (maximo + 1)))]
            partes.append(f'<rect x="{x0 + c * paso}" y="{y0 + fila * paso}" width="{celda}" '
                          f'height="{celda}" rx="2" fill="{color}"/>')
    ultimo_año = sum(d["contributionCount"] for d in dias)
    partes.append(cursiva.path(f"{ultimo_año} contribuciones en el último año", x0, H - 28, 13.5, t["suave"]))
    leyenda_x = W - 28 - 5 * paso
    for i, color in enumerate([t["vacio"]] + t["escala"]):
        partes.append(f'<rect x="{leyenda_x + i * paso}" y="{H - 38}" width="{celda}" height="{celda}" rx="2" fill="{color}"/>')
    return svg(W, H, "Actividad reciente y contribuciones", "".join(partes))


def separador(texto):
    def pieza(t):
        W, H = 830, 46
        ancho = negrita.ancho(texto, 15, espaciado=6)
        x1, x2 = (W - ancho) / 2 - 26, (W + ancho) / 2 + 26
        cuerpo = (
            f'<rect x="20" y="{H / 2}" width="{x1 - 20 - 12}" height="1" fill="{t["borde"]}"/>'
            f'<rect x="{x2 + 12}" y="{H / 2}" width="{W - 20 - x2 - 12}" height="1" fill="{t["borde"]}"/>'
            + rombo(x1, H / 2 + 0.5, 5, t["acento"]) + rombo(x2, H / 2 + 0.5, 5, t["acento"])
            + negrita.path(texto, W / 2, H / 2 + 5.5, 15, t["titulo"], "middle", espaciado=6)
        )
        return svg(W, H, texto.capitalize(), cuerpo)
    return pieza


def tarjeta_sobre_mi(t):
    W = 830
    texto = ("Estoy reforzando Python y SQL para trabajar con datos. En mi tesis estudio cómo los "
             "retrasos en las intervenciones cambian la evolución del contagio financiero y las "
             "estrategias de control.")
    lineas = serif.partir(texto, 17, W - 56)
    y = 84
    partes = [titulo("Sobre mí", 28, 42, t, W - 56)]
    for linea in lineas:
        partes.append(serif.path(linea, 28, y, 17, t["texto"]))
        y += 25
    y += 14
    for grupo, chips in [("Herramientas", ["Python", "TypeScript", "PostgreSQL", "Neon", "Vercel",
                                           "Google Cloud", "Git", "LaTeX"]),
                         ("Intereses", ["Ingeniería de datos", "Modelado", "Sistemas web", "RAG y LLM"])]:
        partes.append(cursiva.path(grupo, 28, y + 18, 15, t["suave"]))
        x = 140
        for chip in chips:
            w = serif.ancho(chip, 15) + 26
            if x + w > W - 28:
                x, y = 140, y + 36
            partes.append(f'<rect x="{x}" y="{y}" width="{w:.1f}" height="27" rx="13.5" fill="{t["chip"]}" '
                          f'stroke="{t["borde"]}" stroke-width="1"/>')
            partes.append(serif.path(chip, x + 13, y + 18.5, 15, t["texto"]))
            x += w + 9
        y += 42
    H = int(y + 14)
    return svg(W, H, "Sobre mí", marco(W, H, t) + "".join(partes))


# Paleta exclusiva de las estadísticas; no modifica las otras piezas del perfil.
PALETA_ESTADISTICAS = {"dark":{"#15191e":"#1b1e23","#30363d":"#363b42","#eee4d6":"#e5e1da","#c8c4c1":"#c8b89a","#92979e":"#a6a9af","#cc514d":"#bd5357","#c8ad8f":"#bd5357","#21262d":"#21262d","#4a1d1b":"#4a2529","#7a2523":"#73383e","#a52f2b":"#a5464b","#d0453a":"#d26869"},"light":{"#f3f1ed":"#f1efeb","#d0d7de":"#d8d2c8","#29221f":"#342c25","#42464a":"#51493d","#656d76":"#62666c","#a23836":"#a33b43","#84664d":"#a33b43","#ebedf0":"#e8e5e1","#e7b3a6":"#e9bec0","#cf7a6c":"#cb878d","#b0463e":"#ac515a"}}
COLORES_LENGUAJES = ["#c8b89a","#819b9b","#b58a57","#a194b0","#758aa3","#8f9092"]

def paleta_estadisticas(tema, paleta):
    mapa = PALETA_ESTADISTICAS[tema]
    return {k: [mapa.get(c, c) for c in v] if isinstance(v, list) else mapa.get(v, v)
            for k, v in paleta.items()}

PIEZAS = {
    "stats": tarjeta_stats,
    "languages": tarjeta_lenguajes,
    "actividad": tarjeta_actividad,
    "separador-proyectos": separador("PROYECTOS SELECCIONADOS"),
    "sobre-mi": tarjeta_sobre_mi,
}

carpeta = Path("cards")
carpeta.mkdir(exist_ok=True)
for nombre, crear in PIEZAS.items():
    for tema, paleta in TEMAS.items():
        contenido = crear(paleta_estadisticas(tema, paleta) if nombre in {'stats', 'languages', 'actividad'} else paleta)
        ET.fromstring(contenido)  # falla si el SVG quedó mal formado
        (carpeta / f"{nombre}-{tema}.svg").write_text(contenido, encoding="utf-8")

print(f"Repositorios: {len(repos)} ({alcance}) · lenguajes: {dict(lenguajes)}")
print(f"Actividad reciente: {[i['repository']['name'] for i in recientes]}")
