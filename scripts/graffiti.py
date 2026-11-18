"""Draw the neon graffiti wall: one year of GitHub contributions sprayed as paint.

Usage:
  GITHUB_TOKEN=... python scripts/graffiti.py          # real data (GitHub Actions)
  python scripts/graffiti.py --fake                     # random data, for previews
"""
import datetime as dt
import math
import json
import os
import random
import sys
import urllib.request

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

USER = "Baldyl66"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "neon", "graffiti.svg")

INK, EDGE = "#0A0814", "#2A1F45"
PINK, CYAN, VIOLET, WHITE, MUTED, DIM = "#FF2E88", "#00E5FF", "#9B5CFF", "#F5F3FF", "#A9A3C7", "#6E6890"
LEVEL_COLORS = {1: VIOLET, 2: CYAN, 3: PINK, 4: PINK}
MONO = "'JetBrains Mono', 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"

# ------------------------------------------------------------------ data
QUERY = """query($login: String!) { user(login: $login) { contributionsCollection {
  contributionCalendar { totalContributions weeks { contributionDays {
    date contributionCount contributionLevel } } } } } }"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "graffiti-wall"})
    data = json.load(urllib.request.urlopen(req, timeout=60))
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["date"], d["contributionCount"], LEVELS[d["contributionLevel"]]) for d in w["contributionDays"]]
             for w in cal["weeks"]]
    return cal["totalContributions"], weeks


def fake():
    rnd = random.Random(4)
    start = dt.date.today() - dt.timedelta(days=364 + (dt.date.today().weekday() + 1) % 7)
    weeks, total = [], 0
    for w in range(53):
        week = []
        for d in range(7):
            day = start + dt.timedelta(days=w * 7 + d)
            if day > dt.date.today():
                break
            c = rnd.choice([0, 0, 0, 1, 2, 3, 5, 8]) if rnd.random() < .6 else 0
            total += c
            lvl = 0 if c == 0 else 1 if c < 2 else 2 if c < 4 else 3 if c < 7 else 4
            week.append((day.isoformat(), c, lvl))
        weeks.append(week)
    return total, weeks


# ------------------------------------------------------------------ display font -> paths
FONT = TTFont(os.path.join(ROOT, "scripts", "fonts", "Anton-Regular.ttf"))
GS, CMAP, UPM, HMTX = FONT.getGlyphSet(), FONT.getBestCmap(), FONT["head"].unitsPerEm, FONT["hmtx"]


def text_path(txt, x, y, size, anchor="start", spacing=0.04):
    s = size / UPM
    names = [CMAP.get(ord(c)) for c in txt]
    width = sum(HMTX[n][0] for n in names if n) * s + spacing * size * (len(txt) - 1)
    x -= width / 2 if anchor == "middle" else width if anchor == "end" else 0
    pen, cx = SVGPathPen(GS), x
    for n in names:
        if n:
            GS[n].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
            cx += HMTX[n][0] * s + spacing * size
    return pen.getCommands(), width


# ------------------------------------------------------------------ drawing
def splat(rnd, cx, cy, lvl, idx):
    """Irregular paint splat with satellite droplets (and a drip for big days)."""
    col = LEVEL_COLORS[lvl]
    base = {1: 3.2, 2: 4.4, 3: 5.4, 4: 6.6}[lvl]
    pts = []
    n = 9
    for k in range(n):
        a = k / n * 6.2832
        r = base * rnd.uniform(.72, 1.18)

        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for k in range(1, n + 1):
        p0, p1 = pts[(k - 1) % n], pts[k % n]
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        d += f" Q{p0[0]:.1f} {p0[1]:.1f} {mx:.1f} {my:.1f}"
    d += "Z"
    drops = ""
    for _ in range(lvl):

        a = rnd.uniform(0, 6.28)
        r = base + rnd.uniform(1.5, 4.5)
        drops += (f'<circle cx="{cx + math.cos(a) * r:.1f}" cy="{cy + math.sin(a) * r:.1f}" '
                  f'r="{rnd.uniform(.6, 1.3):.1f}" fill="{col}"/>')
    drip = ""
    if lvl == 4 and rnd.random() < .7:
        L = rnd.uniform(6, 12)
        drip = (f'<path d="M{cx - 1.3:.1f} {cy:.1f} v{L:.1f} a1.3 1.3 0 0 0 2.6 0 v-{L:.1f}z" fill="{col}"/>')
    glow = f' filter="url(#gl)"' if lvl >= 3 else ""
    return (f'<g class="s" style="animation-delay:{idx * 0.11:.2f}s;transform-origin:{cx:.1f}px {cy:.1f}px">'
            f'<path d="{d}" fill="{col}"{glow}/>{drops}{drip}</g>')


def build(total, weeks):
    W, H = 900, 268
    cell = 15.4
    gx, gy = 34, 104
    rnd = random.Random(total)
    cols = len(weeks)
    grid_w = cols * cell
    gx = (W - grid_w) / 2 + cell / 2

    cells, months, last_month = [], [], None
    for wi, week in enumerate(weeks):
        for di, (date, count, lvl) in enumerate(week):
            cx, cy = gx + wi * cell, gy + di * cell
            if lvl == 0:
                cells.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.3" fill="{EDGE}"/>')
            else:
                cells.append(splat(rnd, cx, cy, lvl, wi))
            if di == 0:
                m = date[5:7]
                if m != last_month and wi < cols - 2:
                    name = dt.date(2000, int(m), 1).strftime("%b").upper()
                    months.append(f'<text x="{cx - 4:.1f}" y="{gy - 18}" class="m">{name}</text>')
                    last_month = m

    sweep = cols * 0.11
    cycle = sweep + 9
    title, tw = text_path("GRAFFITI WALL", 40, 46, 26)
    num, nw = text_path(f"{total:,}".replace(",", " "), W - 40, 46, 26, "end")
    label_x = W - 40 - nw - 10
    legend_x = W - 40 - 4 * 22 - 70
    legend = "".join(
        f'<circle cx="{legend_x + 60 + i * 22}" cy="{H - 26}" r="{[3.2, 4.4, 5.4, 6.6][i]}" fill="{LEVEL_COLORS[i + 1]}"/>'
        for i in range(4))
    nozzle_y = gy + 3 * cell
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <style>
    .m {{ font-family: {MONO}; font-size: 10px; letter-spacing: 1.5px; fill: {DIM}; }}
    .t {{ font-family: {MONO}; font-size: 11px; letter-spacing: 2px; fill: {MUTED}; }}
    .s {{ opacity: 0; transform: scale(0); animation: spray {cycle:.2f}s cubic-bezier(.2,.9,.3,1.3) infinite; }}
    @keyframes spray {{
      0% {{ opacity: 0; transform: scale(0); }}
      2% {{ opacity: 1; transform: scale(1.25); }}
      4% {{ opacity: 1; transform: scale(1); }}
      80% {{ opacity: 1; transform: scale(1); }}
      90%, 100% {{ opacity: 0; transform: scale(.6); }}
    }}
    .noz {{ animation: noz {cycle:.2f}s linear infinite; }}
    @keyframes noz {{
      0% {{ transform: translateX(0); opacity: 1; }}
      {sweep / cycle * 100:.2f}% {{ transform: translateX({grid_w:.0f}px); opacity: 1; }}
      {sweep / cycle * 100 + 1:.2f}%, 100% {{ transform: translateX({grid_w:.0f}px); opacity: 0; }}
    }}
    .pulse {{ animation: pulse 2.6s ease-in-out infinite; }}
    @keyframes pulse {{ 0%,100% {{ opacity: .4; }} 50% {{ opacity: 1; }} }}
  </style>
  <defs>
    <filter id="gl" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <radialGradient id="hp" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(80 20) scale(380 200)">
      <stop offset="0" stop-color="{PINK}" stop-opacity=".22"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>
    <radialGradient id="hc" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(840 240) scale(380 200)">
      <stop offset="0" stop-color="{CYAN}" stop-opacity=".16"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
    <linearGradient id="bd" x1="0" y1="0" x2="{W}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{PINK}"/><stop offset=".5" stop-color="{VIOLET}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
    <pattern id="brick" width="60" height="26" patternUnits="userSpaceOnUse">
      <path d="M0 0H60M0 13H60M0 0V13M30 13V26" fill="none" stroke="{VIOLET}" stroke-opacity=".07"/></pattern>
    <clipPath id="c"><rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="18"/></clipPath>
  </defs>
  <g clip-path="url(#c)">
    <rect width="{W}" height="{H}" fill="{INK}"/>
    <rect width="{W}" height="{H}" fill="url(#brick)"/>
    <rect width="{W}" height="{H}" fill="url(#hp)"/>
    <rect width="{W}" height="{H}" fill="url(#hc)"/>
  </g>
  <rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="18" fill="none" stroke="url(#bd)" stroke-width="2" stroke-opacity=".55"/>
  <path d="{title}" fill="{WHITE}"/>
  <rect x="40" y="53" width="{tw:.0f}" height="3" fill="{PINK}"/>
  <text x="{label_x:.0f}" y="45" text-anchor="end" class="t">CONTRIBUTIONS · LAST YEAR</text>
  <path d="{num}" fill="{CYAN}"/>
  {''.join(months)}
  {''.join(cells)}
  <g class="noz">
    <circle cx="{gx - cell:.1f}" cy="{nozzle_y:.1f}" r="16" fill="{PINK}" fill-opacity=".12"/>
    <circle cx="{gx - cell:.1f}" cy="{nozzle_y:.1f}" r="4" fill="{WHITE}" filter="url(#gl)"/>
    <rect x="{gx - cell - 1:.1f}" y="{gy - 10:.1f}" width="2" height="{6 * cell + 20:.1f}" fill="{PINK}" fill-opacity=".25"/>
  </g>
  <text x="40" y="{H - 22}" class="t">SPRAYED DAILY BY GITHUB ACTIONS</text>
  <text x="{legend_x:.0f}" y="{H - 22}" class="t">LESS</text>
  {legend}
  <text x="{legend_x + 60 + 3 * 22 + 14:.0f}" y="{H - 22}" class="t">MORE</text>
</svg>
"""


if __name__ == "__main__":
    total, weeks = fake() if "--fake" in sys.argv else fetch()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(total, weeks))
    print("graffiti wall:", total, "contributions,", len(weeks), "weeks")
