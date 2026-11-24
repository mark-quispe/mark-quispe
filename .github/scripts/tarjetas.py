"""Genera las tarjetas del perfil (estadísticas y lenguajes) en cards/.

Usa GH_TOKEN. Con un token personal del dueño (STATS_TOKEN) también cuenta los
repositorios privados; con el token automático de Actions solo ve los públicos.
En las tarjetas nunca aparecen nombres de repositorios, solo totales.
"""
import json
import os
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

PROFILE = os.environ["PROFILE"]
TOKEN = os.environ["GH_TOKEN"]

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalRepositoriesWithContributedCommits
      commitContributionsByRepository(maxRepositories: 25) {
        contributions { totalCount }
        repository {
          nameWithOwner name url description pushedAt isPrivate isFork
          primaryLanguage { name }
        }
      }
    }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
      totalCount
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


repos, after = [], None
while True:
    user = graphql({"login": PROFILE, "after": after})
    page = user["repositories"]
    repos += page["nodes"]
    if not page["pageInfo"]["hasNextPage"]:
        break
    after = page["pageInfo"]["endCursor"]

contrib = user["contributionsCollection"]
includes_private = any(repo["isPrivate"] for repo in repos)

sizes, colors = Counter(), {}
for repo in repos:
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        sizes[name] += edge["size"]
        colors[name] = edge["node"]["color"] or "#8694a6"

THEMES = [
    # tema, título, texto, acento
    ("dark", "a98ff7", "c9d1d9", "7ccdf2"),
    ("light", "6443a5", "303742", "397b9b"),
]
FONT = "Segoe UI, Ubuntu, Helvetica Neue, sans-serif"
alcance = "públicos y privados" if includes_private else "públicos"


def card(title, text, purple, body):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="165" viewBox="0 0 400 165">'
        f'<title>{escape(title)}</title>'
        f'<g font-family="{FONT}" fill="#{text}">'
        f'<text x="25" y="33" font-size="18" font-weight="600" fill="#{purple}">{escape(title)}</text>'
        f'{body}</g></svg>'
    )
    ET.fromstring(svg)  # falla si el SVG quedó mal formado
    return svg.encode("utf-8")


def number(n):
    return f"{n:,}".replace(",", " ")


stats_rows = [
    ("Commits (último año)",
     contrib["totalCommitContributions"] + contrib["restrictedContributionsCount"]),
    ("Pull requests (último año)", contrib["totalPullRequestContributions"]),
    ("Repositorios con commits (último año)", contrib["totalRepositoriesWithContributedCommits"]),
    (f"Repositorios propios ({alcance})", len(repos)),
    ("Lenguajes usados", len(sizes)),
]

total = sum(sizes.values())
entries = sizes.most_common(5)
if len(sizes) > 5:
    entries.append(("Otros", total - sum(size for _, size in entries)))
    colors["Otros"] = "#8694a6"

generated = {}
for theme, purple, text, accent in THEMES:
    rows = []
    for i, (label, value) in enumerate(stats_rows):
        y = 64 + i * 20
        rows.append(
            f'<circle cx="30" cy="{y - 4}" r="3.5" fill="#{accent}"/>'
            f'<text x="42" y="{y}" font-size="13">{escape(label)}</text>'
            f'<text x="375" y="{y}" font-size="13" font-weight="700" text-anchor="end">{number(value)}</text>'
        )
    generated[f"stats-{theme}.svg"] = card("Estadísticas de GitHub", text, purple, "".join(rows))

    bars, labels, x = [], [], 25.0
    for i, (language, size) in enumerate(entries):
        width = 350 * size / total
        bars.append(f'<rect x="{x:.3f}" y="55" width="{width:.3f}" height="9" fill="{colors[language]}"/>')
        x += width
        lx, ly = 30 + (i % 2) * 175, 89 + (i // 2) * 18
        percent = f"{100 * size / total:.1f}".replace(".", ",")
        labels.append(f'<circle cx="{lx}" cy="{ly}" r="4" fill="{colors[language]}"/>'
                      f'<text x="{lx + 11}" y="{ly + 4}" font-size="12">'
                      f'{escape(language)} {percent} %</text>')
    if not entries:
        labels.append('<text x="25" y="89" font-size="13">Sin lenguajes detectados</text>')
    body = (
        '<defs><clipPath id="bar"><rect x="25" y="55" width="350" height="9" rx="4.5"/></clipPath></defs>'
        f'<g clip-path="url(#bar)">{"".join(bars)}</g>{"".join(labels)}'
        f'<text x="25" y="151" font-size="11">Por tamaño del código en mis repositorios {alcance}</text>'
    )
    generated[f"languages-{theme}.svg"] = card("Lenguajes más usados", text, purple, body)

folder = Path("cards")
folder.mkdir(exist_ok=True)
for name, data in generated.items():
    (folder / name).write_bytes(data)

print(f"Repositorios: {len(repos)} ({alcance}) · lenguajes: {dict(entries)}")

# --- Sección "Actividad reciente" del README ---------------------------------
# Repos públicos (propios o de organizaciones) con commits míos en el último año,
# ordenados por el último push. Se excluyen privados, forks, el repo del perfil y
# repos sin código.
MESES = "ene feb mar abr may jun jul ago sep oct nov dic".split()
INICIO, FIN = "<!-- recientes:inicio -->", "<!-- recientes:fin -->"

recientes = [
    item for item in contrib["commitContributionsByRepository"]
    if not item["repository"]["isPrivate"]
    and not item["repository"]["isFork"]
    and item["repository"]["primaryLanguage"]
    and item["repository"]["nameWithOwner"].lower() != f"{PROFILE}/{PROFILE}".lower()
]
recientes.sort(key=lambda item: item["repository"]["pushedAt"], reverse=True)

lineas = []
for item in recientes[:4]:
    repo = item["repository"]
    year, month, day = repo["pushedAt"][:10].split("-")
    commits = item["contributions"]["totalCount"]
    detalle = (f'{repo["primaryLanguage"]["name"]} · {commits} {"commits míos" if commits != 1 else "commit mío"}'
               f' · último cambio {int(day)} {MESES[int(month) - 1]} {year}')
    lineas.append(f'- **[{repo["name"]}]({repo["url"]})** <sub>{detalle}</sub>')
    if repo["description"]:
        descripcion = repo["description"].strip()
        if len(descripcion) > 120:
            descripcion = descripcion[:120].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
        lineas.append(f"  {descripcion}")

readme = Path("README.md")
texto = readme.read_text(encoding="utf-8")
if lineas and INICIO in texto and FIN in texto:
    antes, resto = texto.split(INICIO, 1)
    _, despues = resto.split(FIN, 1)
    readme.write_text(f"{antes}{INICIO}\n" + "\n".join(lineas) + f"\n{FIN}{despues}",
                      encoding="utf-8", newline="\n")
    print(f"Actividad reciente: {[item['repository']['name'] for item in recientes[:4]]}")
