"""Draw strategy diagrams (assets/tactics/<map>/*.png) for maps described in MAPS below.

The layout is a schematic, not to scale. Player names come from data/team.json by role and the
legend text from data/<map>.json, so after changing roles or assignments just run again:

    python3 tools/tactics_diagrams.py

Needs Google Chrome (headless) to turn the SVG into PNG; set CHROME=/path/to/chrome if it is
not in the default location. Writes the PNG files and sets "image" on each drawn strategy.
"""
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W, H = 1600, 1000
BG, PANEL, BORDER, TEXT, MUTED = "#16181b", "#1c1f23", "#2a2d31", "#d7dadf", "#8a9099"
CORRIDOR, ZONE, ZONE_STROKE = "#262a2f", "#20242a", "#3a3f46"
GRENADE = {"smoke": "#a7adb5", "flash": "#e3c34a", "molotov": "#e0604e"}
PLAYER_COLORS = {"mendi": "#4aa8e0", "teey": "#6cc06a", "mrpatyk": "#b07ee8", "rond": "#e07bb5", "ciomka": "#4fd1c5"}
SPARE_COLORS = ["#f0a050", "#c9d36a", "#9fb4ff"]
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"
SLOT_FILES = {"pistol": "pistol.png", "A": "execute-a.png", "B": "execute-b.png"}

# Zones: id -> (label, x, y, w, h, kind). Coordinates are centres on a 1600×1000 canvas.
# Each strategy maps a role to its route (zone ids) and throws: (type, from zone, target).
MAPS = {
    "mirage": {
        "zones": {
            "tspawn": ("T spawn", 960, 520, 150, 76, "spawn"),
            "palalley": ("Uliczka pałacowa", 830, 730, 200, 60, ""),
            "rampa": ("Rampa", 640, 720, 110, 52, ""),
            "palace": ("Wnętrze pałacu", 700, 870, 190, 60, ""),
            "asite": ("A", 380, 770, 220, 160, "site"),
            "kanapka": ("Kanapka", 520, 640, 120, 44, ""),
            "poddrewnem": ("Pod drewnem", 540, 890, 140, 44, ""),
            "ct": ("CT", 160, 780, 100, 56, ""),
            "jungle": ("Jungle", 230, 600, 110, 48, ""),
            "schody": ("Schody", 380, 610, 110, 48, ""),
            "topcon": ("Top con", 480, 520, 110, 48, ""),
            "ctspawn": ("CT spawn", 120, 470, 140, 60, "spawn"),
            "okno": ("Okno", 320, 420, 100, 48, ""),
            "mid": ("Mid", 590, 410, 130, 70, ""),
            "topmid": ("Góra środka", 800, 400, 160, 56, ""),
            "short": ("Short", 500, 335, 100, 46, ""),
            "kuchnia": ("Kuchnia", 440, 255, 110, 44, ""),
            "exit": ("Exit", 140, 250, 100, 44, ""),
            "bsite": ("B", 270, 160, 220, 140, "site"),
            "mieszkania": ("Mieszkania", 640, 150, 170, 56, ""),
            "tylna": ("Tylna alejka", 880, 260, 170, 56, ""),
        },
        "links": [
            ("tspawn", "palalley"), ("palalley", "rampa"), ("rampa", "asite"), ("palalley", "palace"),
            ("palace", "asite"), ("asite", "ct"), ("asite", "schody"), ("schody", "jungle"), ("jungle", "ct"),
            ("schody", "topcon"), ("topcon", "mid"), ("jungle", "okno"), ("ct", "ctspawn"), ("okno", "mid"),
            ("mid", "topmid"), ("topmid", "tspawn"), ("mid", "short"), ("short", "kuchnia"), ("kuchnia", "bsite"),
            ("bsite", "exit"), ("exit", "ctspawn"), ("tspawn", "tylna"), ("tylna", "mieszkania"),
            ("mieszkania", "bsite"), ("rampa", "kanapka"), ("palace", "poddrewnem"),
        ],
        "points": {"a_entry": (520, 740), "b_entry": (440, 140), "con": (575, 460)},
        "strategies": {
            "pistol": {
                "entry": {"route": ["tspawn", "tylna", "mieszkania", "bsite"]},
                "second": {"route": ["tspawn", "tylna", "mieszkania", "bsite"],
                           "throws": [("smoke", "tylna", "kuchnia")]},
                "support": {"route": ["tspawn", "tylna", "mieszkania", "bsite"],
                            "throws": [("smoke", "tylna", "short"), ("flash", "mieszkania", "b_entry")]},
                "lurk": {"route": ["tspawn", "tylna", "mieszkania"], "throws": [("smoke", "tylna", "exit")]},
                "awp": {"route": ["tspawn", "topmid", "mid"], "throws": [("smoke", "tspawn", "okno")]},
            },
            "A": {
                "entry": {"route": ["tspawn", "palalley", "rampa", "asite"],
                          "throws": [("smoke", "palalley", "topcon")]},
                "second": {"route": ["tspawn", "palalley", "rampa", "asite"],
                           "throws": [("smoke", "palalley", "ct"), ("molotov", "palalley", "kanapka")]},
                "support": {"route": ["tspawn", "palalley", "rampa", "asite"],
                            "throws": [("smoke", "palalley", "jungle"), ("flash", "palalley", "a_entry")]},
                "lurk": {"route": ["tspawn", "palalley", "palace", "asite"],
                         "throws": [("smoke", "palace", "schody"), ("molotov", "palace", "poddrewnem")]},
                "awp": {"route": ["tspawn", "topmid", "mid"], "throws": [("smoke", "tspawn", "okno")]},
            },
            "B": {
                "entry": {"route": ["tspawn", "tylna", "mieszkania", "bsite"],
                          "throws": [("smoke", "tylna", "exit")]},
                "second": {"route": ["tspawn", "tylna", "mieszkania", "bsite"],
                           "throws": [("smoke", "tylna", "kuchnia"), ("flash", "mieszkania", "b_entry")]},
                "support": {"route": ["tspawn", "tylna", "mieszkania", "bsite"],
                            "throws": [("smoke", "tylna", "short")]},
                "awp": {"route": ["tspawn", "tylna", "mieszkania", "bsite"], "throws": [("smoke", "tspawn", "okno")]},
                "lurk": {"route": ["tspawn", "topmid"], "throws": [("flash", "topmid", "con")]},
            },
        },
    },
    "ancient": {
        "zones": {
            "tspawn": ("T spawn", 560, 890, 150, 70, "spawn"),
            "przeda": ("Przed A", 290, 740, 130, 52, ""),
            "amain": ("A main", 200, 580, 120, 52, ""),
            "asite": ("A", 230, 350, 220, 160, "site"),
            "temple": ("Temple", 360, 210, 120, 46, ""),
            "ct": ("CT", 120, 180, 100, 50, ""),
            "donut": ("Donut", 420, 480, 120, 48, ""),
            "dwor": ("Dwór", 470, 690, 120, 52, ""),
            "mid": ("Mid", 590, 490, 120, 66, ""),
            "red": ("Red", 600, 330, 100, 46, ""),
            "ctspawn": ("CT spawn", 560, 140, 150, 56, "spawn"),
            "cave": ("Cave", 750, 450, 110, 48, ""),
            "bshort": ("B short", 770, 320, 120, 44, ""),
            "bsite": ("B", 900, 280, 220, 150, "site"),
            "blong": ("B long", 1000, 460, 120, 46, ""),
            "ninja": ("Ninja", 1000, 180, 100, 44, ""),
            "bs": ("BS", 880, 150, 80, 42, ""),
            "brama": ("Przed brama", 930, 600, 160, 50, ""),
            "ruiny": ("Ruiny", 820, 720, 120, 52, ""),
            "dolna": ("Dolna strona T", 700, 800, 180, 50, ""),
        },
        "links": [
            ("tspawn", "przeda"), ("przeda", "amain"), ("amain", "asite"), ("asite", "temple"), ("asite", "ct"),
            ("ct", "ctspawn"), ("temple", "ctspawn"), ("asite", "donut"), ("donut", "mid"), ("tspawn", "dwor"),
            ("dwor", "mid"), ("dwor", "przeda"), ("mid", "red"), ("red", "ctspawn"), ("mid", "cave"),
            ("cave", "bshort"), ("bshort", "bsite"), ("tspawn", "dolna"), ("dolna", "ruiny"), ("ruiny", "brama"),
            ("brama", "blong"), ("blong", "bsite"), ("bsite", "ninja"), ("bsite", "bs"), ("bs", "ctspawn"),
        ],
        "points": {"b_entry": (915, 378)},
        "strategies": {
            "pistol": {
                "entry": {"route": ["tspawn", "dolna", "ruiny", "brama", "blong", "bsite"]},
                "second": {"route": ["tspawn", "dolna", "ruiny", "brama", "blong", "bsite"],
                           "throws": [("smoke", "ruiny", "blong")]},
                "support": {"route": ["tspawn", "dolna", "ruiny", "brama", "blong", "bsite"],
                            "throws": [("smoke", "brama", "bshort"), ("flash", "ruiny", "b_entry")]},
                "awp": {"route": ["tspawn", "dolna", "ruiny", "brama", "blong", "bsite"],
                        "throws": [("smoke", "tspawn", "red")]},
                "lurk": {"route": ["tspawn", "dwor", "mid", "cave"]},
            },
            "A": {
                "entry": {"route": ["tspawn", "przeda", "amain", "asite"]},
                "second": {"route": ["tspawn", "przeda", "amain", "asite"],
                           "throws": [("smoke", "przeda", "temple")]},
                "support": {"route": ["tspawn", "dwor", "przeda", "amain", "asite"],
                            "throws": [("smoke", "dwor", "ct")]},
                "lurk": {"route": ["tspawn", "dwor"], "throws": [("smoke", "dwor", "donut")]},
                "awp": {"route": ["tspawn", "dwor", "mid"], "throws": [("smoke", "tspawn", "red")]},
            },
            "B": {
                "entry": {"route": ["tspawn", "dolna", "ruiny", "brama", "blong", "bsite"],
                          "throws": [("flash", "dolna", "b_entry")]},
                "second": {"route": ["tspawn", "dolna", "ruiny", "brama", "blong", "bsite"],
                           "throws": [("smoke", "ruiny", "blong"), ("flash", "ruiny", "b_entry")]},
                "support": {"route": ["tspawn", "dolna", "ruiny", "brama", "blong", "bsite"],
                            "throws": [("smoke", "brama", "bshort"), ("molotov", "dolna", "ninja")]},
                "awp": {"route": ["tspawn", "dolna", "ruiny", "brama", "blong", "bsite"],
                        "throws": [("smoke", "tspawn", "red"), ("molotov", "dolna", "bs")]},
                "lurk": {"route": ["tspawn", "dwor", "mid"], "throws": [("smoke", "dwor", "donut")]},
            },
        },
    },
}

UTILITY_RE = re.compile(r"\b(smoke|flash|molo|incendiary)\w*", re.I)


def esc(s):
    return html.escape(str(s), quote=True)


def text(x, y, s, size=16, fill=TEXT, weight="normal", anchor="start", halo=False):
    extra = f' stroke="{BG}" stroke-width="5" paint-order="stroke"' if halo else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}"{extra}>{s}</text>')


def utility_spans(s):
    """Grenade words in their colours, like the Utility column on the page."""
    out, last = [], 0
    for m in UTILITY_RE.finditer(s):
        out.append(esc(s[last:m.start()]))
        word = m[1].lower()
        kind = "molotov" if word in ("molo", "incendiary") else word
        out.append(f'<tspan fill="{GRENADE[kind]}">{esc(m[0])}</tspan>')
        last = m.end()
    out.append(esc(s[last:]))
    return "".join(out)


def wrap(s, width):
    lines, line = [], ""
    for word in s.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + ([line] if line else [])


def grenade_mark(kind, x, y):
    c = GRENADE[kind]
    if kind == "smoke":
        return f'<circle cx="{x}" cy="{y}" r="30" fill="{c}" fill-opacity=".45" stroke="{c}" stroke-width="2"/>'
    if kind == "molotov":
        return f'<circle cx="{x}" cy="{y}" r="24" fill="{c}" fill-opacity=".5" stroke="{c}" stroke-width="2.5"/>'
    pts = []
    for i in range(16):
        r = 22 if i % 2 == 0 else 9
        a = i * math.pi / 8
        pts.append(f"{x + r * math.cos(a):.1f},{y + r * math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{c}" stroke="{BG}" stroke-width="1.5"/>'


def order_label(timing):
    m = re.match(r"\s*(\d+)", timing or "")
    return m[1] if m else ""


def draw(map_name, accent, slot, strategy, spec, players_by_role, role_names):
    zones, points = spec["zones"], spec["points"]
    where = lambda key: (zones[key][1], zones[key][2]) if key in zones else points[key]
    plan = spec["strategies"][slot]
    rows = [a for a in strategy.get("assignments", []) if a.get("role") in plan]
    roles = [a["role"] for a in rows]
    color = {r: PLAYER_COLORS.get(players_by_role[r]["id"], SPARE_COLORS[i % len(SPARE_COLORS)])
             for i, r in enumerate(roles)}
    shift = {r: ((i - (len(roles) - 1) / 2) * 7) for i, r in enumerate(roles)}

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="{FONT}">', f'<rect width="{W}" height="{H}" fill="{BG}"/>', "<defs>"]
    for r in roles:
        svg.append(f'<marker id="arrow-{r}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" '
                   f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{color[r]}"/></marker>')
    svg.append("</defs>")

    # header
    variant = {"pistol": "Pistolówka", "A": "Execute A", "B": "Execute B"}[slot]
    title = strategy["title"]
    if not title.lower().startswith(variant.lower()):
        title = f"{variant}: {title}"
    svg.append(f'<rect x="30" y="24" width="8" height="44" rx="3" fill="{accent}"/>')
    svg.append(text(52, 57, f"{esc(map_name)} · {esc(title)}", 30, TEXT, "bold"))
    svg.append(f'<rect x="30" y="90" width="1060" height="886" rx="14" fill="{PANEL}" stroke="{BORDER}"/>')

    # map
    for a, b in spec["links"]:
        (x1, y1), (x2, y2) = where(a), where(b)
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{CORRIDOR}" stroke-width="34" '
                   f'stroke-linecap="round"/>')
    for label, x, y, w, h, kind in zones.values():
        if kind == "site":
            svg.append(f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" rx="16" fill="{accent}" '
                       f'fill-opacity=".14" stroke="{accent}" stroke-width="2"/>')
            svg.append(text(x, y + 26, label, 76, accent, "bold", "middle"))
        else:
            dash = ' stroke-dasharray="6 5"' if kind == "spawn" else ""
            svg.append(f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" rx="10" fill="{ZONE}" '
                       f'stroke="{ZONE_STROKE}" stroke-width="1.5"{dash}/>')

    # routes
    for r in roles:
        pts = [where(z) for z in plan[r]["route"]]
        d = " ".join(f"{x + shift[r]:.1f},{y + shift[r]:.1f}" for x, y in pts)
        svg.append(f'<polyline points="{d}" fill="none" stroke="{color[r]}" stroke-width="5" stroke-opacity=".9" '
                   f'stroke-linejoin="round" stroke-linecap="round" marker-end="url(#arrow-{r})"/>')

    # throws: dashed line from the throw spot, mark on the target, thrower's name under it
    marks, names, per_target = [], [], {}
    for r in roles:
        for kind, src, dst in plan[r].get("throws", []):
            per_target.setdefault(dst, []).append((r, kind, src))
    for dst, items in per_target.items():
        tx, ty = where(dst)
        for k, (r, kind, src) in enumerate(items):
            x = tx + (k - (len(items) - 1) / 2) * 72
            sx, sy = where(src)
            svg.append(f'<line x1="{sx + shift[r]:.1f}" y1="{sy + shift[r]:.1f}" x2="{x}" y2="{ty}" '
                       f'stroke="{GRENADE[kind]}" stroke-width="2.5" stroke-dasharray="9 7" stroke-opacity=".85"/>')
            marks.append(grenade_mark(kind, x, ty))
            names.append(text(x, ty + 50, esc(players_by_role[r]["name"]), 15, color[r], "bold", "middle", halo=True))
    svg += marks

    # zone names above routes and grenades so they stay readable
    for label, x, y, w, h, kind in zones.values():
        if kind != "site":
            svg.append(text(x, y + 6, esc(label), 17, TEXT, "bold", "middle", halo=True))
    svg += names

    # entry order: inside the bottom of a site, or to the right of any other zone
    ends = {}
    for a in rows:
        if order_label(a.get("timing")):
            ends.setdefault(plan[a["role"]]["route"][-1], []).append(a)
    for end, items in ends.items():
        ex, ey = where(end)
        _, _, _, w, h, kind = zones[end]
        for k, a in enumerate(items):
            if kind == "site":
                x, y = ex + (k - (len(items) - 1) / 2) * 34, ey + h / 2 - 22
            else:
                x, y = ex + w / 2 + 22 + k * 34, ey
            r = a["role"]
            svg.append(f'<circle cx="{x}" cy="{y}" r="15" fill="{color[r]}" stroke="{BG}" stroke-width="2"/>')
            svg.append(text(x, y + 5.5, order_label(a.get("timing")), 15, BG, "bold", "middle"))

    # legend
    lx, ly = 1110, 90
    svg.append(f'<rect x="{lx}" y="{ly}" width="460" height="886" rx="14" fill="{PANEL}" stroke="{BORDER}"/>')
    svg.append(text(lx + 24, ly + 42, "Kto co robi", 22, TEXT, "bold"))
    y = ly + 80
    for a in rows:
        r = a["role"]
        order = order_label(a.get("timing"))
        head = f"{order + '.  ' if order else ''}{esc(players_by_role[r]['name'])}"
        util = wrap(a.get("utility") or "—", 40)
        block = 50 + 22 * len(util)
        svg.append(f'<rect x="{lx + 24}" y="{y - 20}" width="6" height="{block - 14}" rx="3" fill="{color[r]}"/>')
        svg.append(text(lx + 42, y, f'{head} <tspan fill="{MUTED}" font-weight="normal">· '
                                    f'{esc(role_names.get(r, r))}</tspan>', 20, color[r], "bold"))
        svg.append(text(lx + 42, y + 24, esc(a.get("position", "")), 15, MUTED))
        for i, line in enumerate(util):
            svg.append(text(lx + 42, y + 48 + 22 * i, utility_spans(line), 16))
        y += block + 12

    # key
    ky = ly + 886 - 150
    svg.append(f'<line x1="{lx + 24}" y1="{ky - 24}" x2="{lx + 436}" y2="{ky - 24}" stroke="{BORDER}"/>')
    key = [("smoke", "smoke"), ("flash", "flash"), ("molotov", "molotov")]
    for i, (kind, label) in enumerate(key):
        kx = lx + 50 + i * 140
        svg.append(grenade_mark(kind, kx, ky + 4).replace('r="30"', 'r="14"').replace('r="24"', 'r="12"'))
        svg.append(text(kx + 24, ky + 10, label, 16, GRENADE[kind]))
    svg.append(f'<line x1="{lx + 36}" y1="{ky + 48}" x2="{lx + 96}" y2="{ky + 48}" stroke="{GRENADE["smoke"]}" '
               f'stroke-width="2.5" stroke-dasharray="9 7"/>')
    svg.append(text(lx + 108, ky + 54, "rzut: skąd → gdzie", 16, MUTED))
    svg.append(f'<line x1="{lx + 260}" y1="{ky + 48}" x2="{lx + 310}" y2="{ky + 48}" stroke="{TEXT}" stroke-width="5"/>')
    svg.append(text(lx + 322, ky + 54, "trasa gracza", 16, MUTED))
    svg.append(text(lx + 24, ky + 96, "Schemat poglądowy, nie w skali. Liczby = kolejność wejścia.", 14, MUTED))
    svg.append(text(lx + 24, ky + 118, "Lineupy granatów: zakładka Lineupy → Teey.", 14, MUTED))
    svg.append("</svg>")
    return "\n".join(svg)


def find_chrome():
    candidates = [os.environ.get("CHROME"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome")]
    for c in candidates:
        if c and Path(c).exists():
            return c
    sys.exit("Nie znaleziono Chrome — ustaw zmienną CHROME na ścieżkę do przeglądarki.")


def render_png(chrome, svg_path, png_path, profile):
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--user-data-dir={profile}", f"--window-size={W},{H}", f"--screenshot={png_path}",
                    svg_path.as_uri()], check=True, capture_output=True)


def main():
    chrome = find_chrome()
    team = json.loads((ROOT / "data/team.json").read_text(encoding="utf-8"))
    maps = {m["id"]: m for m in json.loads((ROOT / "data/maps.json").read_text(encoding="utf-8"))["maps"]}
    role_names = {r["id"]: r["name"] for r in team["roles"]}
    players_by_role = {p["role"]: p for p in team["players"] if p.get("role") and p.get("status") == "active"}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for map_id, spec in MAPS.items():
            path = ROOT / f"data/{map_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            s = data["strategies"]
            for slot in SLOT_FILES:
                holder, key = (s, "pistol") if slot == "pistol" else (s.get("execute") or {}, slot)
                strategy = holder.get(key)
                if not strategy or slot not in spec["strategies"]:
                    continue
                svg_path = tmp / f"{map_id}-{slot}.svg"
                svg_path.write_text(draw(maps[map_id]["name"], maps[map_id].get("accent", "#6a9f5b"), slot,
                                         strategy, spec, players_by_role, role_names), encoding="utf-8")
                rel = f"assets/tactics/{map_id}/{SLOT_FILES[slot]}"
                render_png(chrome, svg_path, ROOT / rel, tmp / "chrome-profile")
                # keep "image" right after "summary", as in the README format
                holder[key] = {}
                for k, v in strategy.items():
                    if k != "image":
                        holder[key][k] = v
                    if k == "summary":
                        holder[key]["image"] = rel
                holder[key].setdefault("image", rel)
                print("narysowano", rel)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
