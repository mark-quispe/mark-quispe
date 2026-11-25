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
    cuerpo = [marco(W, H, t)]
    cuerpo.append(negrita.path("Estadísticas de GitHub", 23, 27, 20, t["titulo"]))
    cuerpo.append(rombo(374, 21, 4, t["acento"]))
    cuerpo.append(f'<path d="M23 37H377" stroke="{t["borde"]}" stroke-width="1"/>')
    cuerpo.append(f'<path d="M200 49V112M23 120H377M142 130V186M258 130V186" stroke="{t["borde"]}" stroke-width=".8" opacity=".8"/>')
    # Line icons: commit history and pull request.
    cuerpo.append(f'<g fill="none" stroke="{t["acento"]}" stroke-width="1.5"><path d="M27 57H47"/><circle cx="37" cy="57" r="4" fill="{t["fondo"]}"/><path d="M218 51V66M218 56Q232 56 232 66"/><circle cx="218" cy="51" r="2.4" fill="{t["fondo"]}"/><circle cx="218" cy="66" r="2.4" fill="{t["fondo"]}"/><circle cx="232" cy="66" r="2.4" fill="{t["fondo"]}"/></g>')
    for x, label, value in [(26, "Commits", estadisticas[0][1]), (215, "Pull requests", estadisticas[1][1])]:
        cuerpo.append(negrita.path(f"{value:,}".replace(",", " "), x + 30, 85, 37, t["titulo"]))
        cuerpo.append(serif.path(label, x, 101, 14, t["texto"]))
        cuerpo.append(serif.path("Último año", x, 113, 10.5, t["suave"]))
    for x, value, labels in [
        (26, estadisticas[2][1], ("Repositorios", "con commits")),
        (154, estadisticas[3][1], ("Repositorios", alcance)),
        (270, estadisticas[4][1], ("Lenguajes", "usados")),
    ]:
        cuerpo.append(rombo(x+3, 140, 3, t["acento"]))
        cuerpo.append(negrita.path(f"{value:,}".replace(",", " "), x+13, 152, 27, t["titulo"]))
        cuerpo.append(serif.path(labels[0], x, 169, 13, t["texto"]))
        cuerpo.append(serif.path(labels[1], x, 182, 11.5, t["suave"]))
    return svg(W, H, "Estadísticas de GitHub", "".join(cuerpo))


def tarjeta_lenguajes(t):
    tonos = tonos_lenguajes()
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
        W, H = 830, 28
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
COLORES_LENGUAJES = {"TypeScript":"#c8b89a","Python":"#9b4758","JavaScript":"#b08d57","CSS":"#527d78","PLpgSQL":"#758aa3","Otros":"#8f9092","HTML":"#b98265","SQL":"#a194b0","Shell":"#a63d40","Go":"#73918e","Java":"#b7a078","C++":"#8f829c","C":"#8896a4","Rust":"#a96e50","C#":"#9e8b9c"}
TONOS_ALTERNATIVOS = ["#b98265", "#a194b0", "#a63d40", "#73918e", "#b7a078", "#8896a4"]

def tonos_lenguajes():
    tonos = {nombre: COLORES_LENGUAJES[nombre] for nombre, _ in lenguajes
             if nombre in COLORES_LENGUAJES}
    disponibles = iter(c for c in TONOS_ALTERNATIVOS if c not in tonos.values())
    for nombre, _ in sorted(lenguajes):
        if nombre not in tonos:
            tonos[nombre] = next(disponibles)
    return tonos

def paleta_estadisticas(tema, paleta):
    mapa = PALETA_ESTADISTICAS[tema]
    return {k: [mapa.get(c, c) for c in v] if isinstance(v, list) else mapa.get(v, v)
            for k, v in paleta.items()}

PIEZAS = {
    "stats": tarjeta_stats,
    "languages": tarjeta_lenguajes,
    "actividad": tarjeta_actividad,
    "separador-proyectos-compacto": separador("PROYECTOS SELECCIONADOS"),
    "sobre-mi": tarjeta_sobre_mi,
}

carpeta = Path("cards")
carpeta.mkdir(exist_ok=True)
for nombre, crear in PIEZAS.items():
    for tema, paleta in TEMAS.items():
        colores = paleta_estadisticas(tema, paleta) if nombre in {'stats', 'languages', 'actividad'} else paleta
        if tema == 'dark' and nombre in {'stats', 'languages'}:
            colores = {**colores, 'fondo': '#15191e'}
        contenido = crear(colores)
        ET.fromstring(contenido)  # falla si el SVG quedó mal formado
        (carpeta / f"{nombre}-{tema}.svg").write_text(contenido, encoding="utf-8")

print(f"Repositorios: {len(repos)} ({alcance}) · lenguajes: {dict(lenguajes)}")
print(f"Actividad reciente: {[i['repository']['name'] for i in recientes]}")


# Composición vertical para mostrar las dos estadísticas sin una tabla HTML.
ET.register_namespace("", "http://www.w3.org/2000/svg")
ns = "{http://www.w3.org/2000/svg}"
for tema in TEMAS:
    combinado = ET.Element(ns + "svg", {
        "width": "400", "height": "488", "viewBox": "0 0 400 488", "role": "img"
    })
    ET.SubElement(combinado, ns + "title").text = "Estadísticas y lenguajes de GitHub"
    for nombre, prefijo, y in (("stats", "s-", 18), ("languages", "l-", 260)):
        pieza = ET.fromstring((carpeta / f"{nombre}-{tema}.svg").read_text(encoding="utf-8"))
        pieza.set("x", "0")
        pieza.set("y", str(y))
        for elemento in pieza.iter():
            if "id" in elemento.attrib:
                elemento.set("id", prefijo + elemento.get("id"))
            for clave, valor in list(elemento.attrib.items()):
                if clave.endswith("href") and valor.startswith("#"):
                    elemento.set(clave, "#" + prefijo + valor[1:])
                elif "url(#" in valor:
                    elemento.set(clave, valor.replace("url(#", "url(#" + prefijo))
        combinado.append(pieza)
    filigranas = {"dark": "<g xmlns=\"http://www.w3.org/2000/svg\" transform=\"translate(200 241) scale(1 .87)\" fill=\"none\" stroke-width=\".85\" stroke-linecap=\"round\" stroke-linejoin=\"round\" opacity=\".82\"><path d=\"M0 16 C-2 4 -3 -10 0 -23 C7 -15 11 -7 7 0 C4 7 3 12 0 16\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.015;0.300;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 12 C-9 3 -14 -7 -11 -17 C-5 -15 -1 -9 0 -3\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.029;0.314;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 12 C9 3 14 -7 11 -17 C5 -15 1 -9 0 -3\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.043;0.328;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 16 C-12 12 -19 2 -22 -9 C-13 -9 -8 -1 -4 6\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.057;0.342;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 16 C12 12 19 2 22 -9 C13 -9 8 -1 4 6\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.071;0.356;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 17 Q-11 19 -17 17 L-9 12 M0 17 Q11 19 17 17 L9 12\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.085;0.370;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 -20 Q3 -8 0 13\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.099;0.384;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><g><path d=\"M0 16 C18 4 36 -13 58 -11 C87 -9 96 13 120 11 C135 10 145 0 153 4 C160 8 154 15 149 12\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.015;0.300;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M7 16 C34 20 49 4 72 5 C93 5 105 17 125 16 C140 15 150 8 154 6\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.029;0.314;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M17 9 C23 -3 26 -10 32 -15 C34 -7 30 1 24 6 C21 9 19 10 17 9\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.043;0.328;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M29 2 C33 -7 41 -17 47 -19 C47 -10 41 -5 35 -2\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.057;0.342;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M42 -7 C50 -18 60 -20 69 -17 C63 -11 55 -9 49 -10\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.071;0.356;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M57 -11 C68 -19 83 -17 92 -10 C79 -13 75 -8 67 -8\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.085;0.370;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M71 -6 C76 1 87 3 96 0 C90 -4 82 -7 77 -7\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.099;0.384;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M82 -2 C91 -2 100 -9 105 -15 C109 -5 102 2 96 4\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.113;0.398;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M96 6 C110 4 116 -3 121 -10 C124 -1 119 8 111 10\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.127;0.412;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M111 11 C119 16 128 20 137 15 C132 10 125 11 121 11\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.141;0.426;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M126 11 C137 3 143 -3 150 -3 C147 2 143 6 138 8\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.155;0.440;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M13 14 C23 13 29 16 33 21 C24 24 17 19 13 14\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.169;0.454;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M38 12 C49 12 57 17 60 21 C50 23 43 19 38 12\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.183;0.468;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M61 6 C68 12 77 15 84 13 C78 8 73 7 67 6\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.197;0.482;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M36 0 Q42 -8 47 -14 M51 -9 Q60 -14 67 -15 M100 3 Q105 -2 104 -10 M116 8 Q119 1 121 -6\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.211;0.496;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M22 8 Q26 0 30 -9 M66 -9 Q78 -14 88 -11 M118 14 Q128 17 133 16\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.225;0.510;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M4 18 C-1 23 -8 22 -11 19\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.239;0.524;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path></g><g transform=\"scale(-1 1)\"><path d=\"M0 16 C18 4 36 -13 58 -11 C87 -9 96 13 120 11 C135 10 145 0 153 4 C160 8 154 15 149 12\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.015;0.300;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M7 16 C34 20 49 4 72 5 C93 5 105 17 125 16 C140 15 150 8 154 6\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.029;0.314;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M17 9 C23 -3 26 -10 32 -15 C34 -7 30 1 24 6 C21 9 19 10 17 9\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.043;0.328;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M29 2 C33 -7 41 -17 47 -19 C47 -10 41 -5 35 -2\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.057;0.342;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M42 -7 C50 -18 60 -20 69 -17 C63 -11 55 -9 49 -10\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.071;0.356;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M57 -11 C68 -19 83 -17 92 -10 C79 -13 75 -8 67 -8\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.085;0.370;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M71 -6 C76 1 87 3 96 0 C90 -4 82 -7 77 -7\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.099;0.384;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M82 -2 C91 -2 100 -9 105 -15 C109 -5 102 2 96 4\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.113;0.398;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M96 6 C110 4 116 -3 121 -10 C124 -1 119 8 111 10\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.127;0.412;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M111 11 C119 16 128 20 137 15 C132 10 125 11 121 11\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.141;0.426;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M126 11 C137 3 143 -3 150 -3 C147 2 143 6 138 8\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.155;0.440;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M13 14 C23 13 29 16 33 21 C24 24 17 19 13 14\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.169;0.454;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M38 12 C49 12 57 17 60 21 C50 23 43 19 38 12\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.183;0.468;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M61 6 C68 12 77 15 84 13 C78 8 73 7 67 6\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.197;0.482;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M36 0 Q42 -8 47 -14 M51 -9 Q60 -14 67 -15 M100 3 Q105 -2 104 -10 M116 8 Q119 1 121 -6\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.211;0.496;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M22 8 Q26 0 30 -9 M66 -9 Q78 -14 88 -11 M118 14 Q128 17 133 16\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.225;0.510;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M4 18 C-1 23 -8 22 -11 19\" pathLength=\"100\" stroke=\"#b99a72\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.239;0.524;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path></g><path d=\"M0 18 L3 21 L0 24 L-3 21 Z\" pathLength=\"100\" stroke=\"#a64d50\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.099;0.384;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><animate attributeName=\"opacity\" values=\".82;.82;0;0;.82\" keyTimes=\"0;.78;.90;.99;1\" dur=\"7s\" repeatCount=\"indefinite\"/></g>", "light": "<g xmlns=\"http://www.w3.org/2000/svg\" transform=\"translate(200 241) scale(1 .87)\" fill=\"none\" stroke-width=\".85\" stroke-linecap=\"round\" stroke-linejoin=\"round\" opacity=\".82\"><path d=\"M0 16 C-2 4 -3 -10 0 -23 C7 -15 11 -7 7 0 C4 7 3 12 0 16\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.015;0.300;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 12 C-9 3 -14 -7 -11 -17 C-5 -15 -1 -9 0 -3\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.029;0.314;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 12 C9 3 14 -7 11 -17 C5 -15 1 -9 0 -3\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.043;0.328;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 16 C-12 12 -19 2 -22 -9 C-13 -9 -8 -1 -4 6\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.057;0.342;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 16 C12 12 19 2 22 -9 C13 -9 8 -1 4 6\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.071;0.356;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 17 Q-11 19 -17 17 L-9 12 M0 17 Q11 19 17 17 L9 12\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.085;0.370;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M0 -20 Q3 -8 0 13\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.099;0.384;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><g><path d=\"M0 16 C18 4 36 -13 58 -11 C87 -9 96 13 120 11 C135 10 145 0 153 4 C160 8 154 15 149 12\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.015;0.300;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M7 16 C34 20 49 4 72 5 C93 5 105 17 125 16 C140 15 150 8 154 6\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.029;0.314;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M17 9 C23 -3 26 -10 32 -15 C34 -7 30 1 24 6 C21 9 19 10 17 9\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.043;0.328;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M29 2 C33 -7 41 -17 47 -19 C47 -10 41 -5 35 -2\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.057;0.342;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M42 -7 C50 -18 60 -20 69 -17 C63 -11 55 -9 49 -10\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.071;0.356;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M57 -11 C68 -19 83 -17 92 -10 C79 -13 75 -8 67 -8\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.085;0.370;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M71 -6 C76 1 87 3 96 0 C90 -4 82 -7 77 -7\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.099;0.384;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M82 -2 C91 -2 100 -9 105 -15 C109 -5 102 2 96 4\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.113;0.398;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M96 6 C110 4 116 -3 121 -10 C124 -1 119 8 111 10\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.127;0.412;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M111 11 C119 16 128 20 137 15 C132 10 125 11 121 11\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.141;0.426;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M126 11 C137 3 143 -3 150 -3 C147 2 143 6 138 8\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.155;0.440;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M13 14 C23 13 29 16 33 21 C24 24 17 19 13 14\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.169;0.454;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M38 12 C49 12 57 17 60 21 C50 23 43 19 38 12\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.183;0.468;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M61 6 C68 12 77 15 84 13 C78 8 73 7 67 6\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.197;0.482;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M36 0 Q42 -8 47 -14 M51 -9 Q60 -14 67 -15 M100 3 Q105 -2 104 -10 M116 8 Q119 1 121 -6\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.211;0.496;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M22 8 Q26 0 30 -9 M66 -9 Q78 -14 88 -11 M118 14 Q128 17 133 16\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.225;0.510;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M4 18 C-1 23 -8 22 -11 19\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.239;0.524;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path></g><g transform=\"scale(-1 1)\"><path d=\"M0 16 C18 4 36 -13 58 -11 C87 -9 96 13 120 11 C135 10 145 0 153 4 C160 8 154 15 149 12\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.015;0.300;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M7 16 C34 20 49 4 72 5 C93 5 105 17 125 16 C140 15 150 8 154 6\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.029;0.314;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M17 9 C23 -3 26 -10 32 -15 C34 -7 30 1 24 6 C21 9 19 10 17 9\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.043;0.328;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M29 2 C33 -7 41 -17 47 -19 C47 -10 41 -5 35 -2\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.057;0.342;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M42 -7 C50 -18 60 -20 69 -17 C63 -11 55 -9 49 -10\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.071;0.356;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M57 -11 C68 -19 83 -17 92 -10 C79 -13 75 -8 67 -8\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.085;0.370;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M71 -6 C76 1 87 3 96 0 C90 -4 82 -7 77 -7\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.099;0.384;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M82 -2 C91 -2 100 -9 105 -15 C109 -5 102 2 96 4\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.113;0.398;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M96 6 C110 4 116 -3 121 -10 C124 -1 119 8 111 10\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.127;0.412;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M111 11 C119 16 128 20 137 15 C132 10 125 11 121 11\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.141;0.426;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M126 11 C137 3 143 -3 150 -3 C147 2 143 6 138 8\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.155;0.440;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M13 14 C23 13 29 16 33 21 C24 24 17 19 13 14\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.169;0.454;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M38 12 C49 12 57 17 60 21 C50 23 43 19 38 12\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.183;0.468;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M61 6 C68 12 77 15 84 13 C78 8 73 7 67 6\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.197;0.482;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M36 0 Q42 -8 47 -14 M51 -9 Q60 -14 67 -15 M100 3 Q105 -2 104 -10 M116 8 Q119 1 121 -6\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.211;0.496;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M22 8 Q26 0 30 -9 M66 -9 Q78 -14 88 -11 M118 14 Q128 17 133 16\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.225;0.510;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><path d=\"M4 18 C-1 23 -8 22 -11 19\" pathLength=\"100\" stroke=\"#94734a\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.239;0.524;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path></g><path d=\"M0 18 L3 21 L0 24 L-3 21 Z\" pathLength=\"100\" stroke=\"#a33b43\" stroke-dasharray=\"100\" stroke-dashoffset=\"0\"><animate attributeName=\"stroke-dashoffset\" values=\"100;100;0;0;100\" keyTimes=\"0;0.099;0.384;0.86;1\" dur=\"7s\" repeatCount=\"indefinite\"/></path><animate attributeName=\"opacity\" values=\".82;.82;0;0;.82\" keyTimes=\"0;.78;.90;.99;1\" dur=\"7s\" repeatCount=\"indefinite\"/></g>"}
    combinado.append(ET.fromstring(filigranas[tema]))
    ET.ElementTree(combinado).write(carpeta / f"resumen-acanthus-{tema}.svg", encoding="unicode")
