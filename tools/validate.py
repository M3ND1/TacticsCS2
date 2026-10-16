#!/usr/bin/env python3
"""Sprawdza dane CS2 Playbook przed pushem.

Użycie (z katalogu repozytorium):
    python3 tools/validate.py              # sprawdza repozytorium, w którym leży ten plik
    python3 tools/validate.py ścieżka/do/repo

Kod wyjścia 0 = brak problemów, 1 = wypisano problemy.
"""
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

MAP_ID_RE = re.compile(r"^[a-z0-9-]+$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
LINEUP_REQUIRED = ("id", "player", "name", "target", "side", "type", "aspect", "image")
ASPECTS = ("4:3", "4:3 stretched", "16:9", "21:9")
TYPES = ("smoke", "flash", "molotov")
STRATEGY_SLOTS = ("pistol", "execute", "backup")
VARIANTS = ("A", "B")
RELATIVE_HINT = "musi być względna (bez / na początku, bez .., bez http)"


def is_obj(x):
    return isinstance(x, dict)


def is_text(x):
    return isinstance(x, str) and x.strip() != ""


def is_relative_path(p):
    return (
        is_text(p)
        and not p.startswith("/")
        and not SCHEME_RE.match(p)
        and ".." not in p.split("/")
    )


def load_json(root, rel, tracked=None):
    """Return (data, problems). data is None when the file is missing, mis-cased or invalid."""
    actual = find_exact(root, rel)
    if actual is None:
        return None, [f"{rel}: brak pliku"]
    if actual != rel:
        return None, [
            f'{rel}: wielkość liter w nazwie pliku nie zgadza się z "{actual}" '
            "— GitHub Pages rozróżnia wielkość liter"
        ]
    problems = check_tracked(tracked, rel, rel)
    try:
        with open(Path(root) / rel, encoding="utf-8-sig") as fh:
            return json.load(fh), problems
    except json.JSONDecodeError as e:
        return None, problems + [f"{rel}: błąd składni JSON — linia {e.lineno}, kolumna {e.colno} ({e.msg})"]
    except UnicodeDecodeError:
        return None, problems + [f"{rel}: plik nie jest zapisany w UTF-8"]


def check_maps_index(data):
    f = "data/maps.json"
    if not is_obj(data) or not isinstance(data.get("maps"), list):
        return [f'{f}: oczekiwano obiektu z listą "maps"']
    out, seen = [], set()
    for i, m in enumerate(data["maps"]):
        if not is_obj(m) or not is_text(m.get("id")):
            out.append(f'{f}: maps[{i}] musi mieć "id" (tekst)')
            continue
        mid = m["id"]
        if not MAP_ID_RE.match(mid):
            out.append(f'{f}: id mapy "{mid}" może zawierać tylko a-z, 0-9 i -')
        if mid in seen:
            out.append(f'{f}: zduplikowane id mapy "{mid}"')
        seen.add(mid)
        if not is_text(m.get("name")):
            out.append(f'{f}: mapa "{mid}" nie ma "name"')
        if m.get("accent") is not None and not (isinstance(m["accent"], str) and HEX_RE.match(m["accent"])):
            out.append(f'{f}: mapa "{mid}": "accent" musi być kolorem w formacie #RRGGBB')
    return out


def team_ids(team, key):
    """Set of ids under team[key], or None when team data is unusable (reported elsewhere)."""
    if not is_obj(team) or not isinstance(team.get(key), list):
        return None
    return {x["id"] for x in team[key] if is_obj(x) and is_text(x.get("id"))}


def check_team(team):
    f = "data/team.json"
    if not is_obj(team):
        return [f'{f}: oczekiwano obiektu z listami "roles" i "players"']
    out = []

    def p(msg):
        out.append(f"{f}: {msg}")

    roles = team.get("roles")
    players = team.get("players")
    if not isinstance(roles, list):
        p('brak listy "roles"')
        roles = []
    if not isinstance(players, list):
        p('brak listy "players"')
        players = []

    role_ids = set()
    for i, r in enumerate(roles):
        if not is_obj(r) or not is_text(r.get("id")):
            p(f'roles[{i}] musi mieć "id" (tekst)')
            continue
        if r["id"] in role_ids:
            p(f'zduplikowane id roli "{r["id"]}"')
        role_ids.add(r["id"])
        if not is_text(r.get("name")):
            p(f'rola "{r["id"]}" nie ma "name"')

    player_ids = set()
    holders = {}
    for i, pl in enumerate(players):
        if not is_obj(pl) or not is_text(pl.get("id")):
            p(f'players[{i}] musi mieć "id" (tekst)')
            continue
        pid = pl["id"]
        if pid in player_ids:
            p(f'zduplikowane id gracza "{pid}"')
        player_ids.add(pid)
        if not is_text(pl.get("name")):
            p(f'gracz "{pid}" nie ma "name"')
        status = pl.get("status")
        if status not in ("active", "sub"):
            p(f'gracz "{pid}": "status" musi być "active" albo "sub"')
        if pl.get("aspect") is not None and pl["aspect"] not in ASPECTS:
            p(f'gracz "{pid}": "aspect" musi być jednym z: {", ".join(ASPECTS)} albo null')
        role = pl.get("role")
        if role is None:
            continue
        if not isinstance(role, str) or role not in role_ids:
            p(f'gracz "{pid}": nieznana rola "{role}"')
            continue
        if status in ("active", "sub"):
            holders.setdefault(role, {"active": [], "sub": []})[status].append(pid)

    for role, by_status in holders.items():
        if len(by_status["active"]) > 1:
            p(f'rola "{role}" ma kilku aktywnych graczy: {", ".join(by_status["active"])}')
        if len(by_status["sub"]) > 1:
            p(f'rola "{role}" ma kilku rezerwowych: {", ".join(by_status["sub"])}')
    return out


def check_strategy(st, label, role_ids, p):
    if st is None:
        return
    if not is_obj(st):
        p(f'strategia "{label}" musi być obiektem albo null')
        return
    if not is_text(st.get("title")):
        p(f'strategia "{label}" nie ma "title"')
    if st.get("image") is not None and not is_relative_path(st["image"]):
        p(f'strategia "{label}": ścieżka "image" {RELATIVE_HINT}')
    steps = st.get("steps")
    if steps is not None and not (isinstance(steps, list) and all(isinstance(s, str) for s in steps)):
        p(f'strategia "{label}": "steps" musi być listą tekstów')
    assignments = st.get("assignments")
    if assignments is None:
        return
    if not isinstance(assignments, list):
        p(f'strategia "{label}": "assignments" musi być listą')
        return
    for i, a in enumerate(assignments):
        role = a.get("role") if is_obj(a) else None
        if role_ids is not None and (not isinstance(role, str) or role not in role_ids):
            p(f'strategia "{label}": nieznana rola "{role if role is not None else ""}" w assignments[{i}]')


def check_map(data, map_id, team):
    f = f"data/{map_id}.json"
    out = []

    def p(msg):
        out.append(f"{f}: {msg}")

    if not is_obj(data):
        p("oczekiwano obiektu")
        return out
    if data.get("id") != map_id:
        p(f'"id" w pliku ("{data.get("id")}") nie zgadza się z data/maps.json ("{map_id}")')

    role_ids = team_ids(team, "roles")
    player_ids = team_ids(team, "players")

    if "strategies" not in data:
        p('brak "strategies"')
    elif not is_obj(data["strategies"]):
        p('"strategies" musi być obiektem')
    else:
        s = data["strategies"]
        for k in s:
            if k not in STRATEGY_SLOTS:
                p(f'nieznany klucz "{k}" w "strategies" (dozwolone: {", ".join(STRATEGY_SLOTS)})')
        check_strategy(s.get("pistol"), "pistol", role_ids, p)
        check_strategy(s.get("backup"), "backup", role_ids, p)
        ex = s.get("execute")
        if ex is not None and not is_obj(ex):
            p('"strategies.execute" musi być obiektem z kluczami "A" i "B"')
        elif is_obj(ex):
            for k in ex:
                if k not in VARIANTS:
                    p(f'nieznany klucz "{k}" w "strategies.execute" (dozwolone: {", ".join(VARIANTS)})')
            for variant in VARIANTS:
                check_strategy(ex.get(variant), f"execute.{variant}", role_ids, p)

    lineups = data.get("lineups")
    if lineups is not None and not isinstance(lineups, list):
        p('"lineups" musi być listą')
        lineups = []
    seen = set()
    for i, l in enumerate(lineups or []):
        if not is_obj(l):
            p(f"lineups[{i}] musi być obiektem")
            continue
        name = l["id"] if is_text(l.get("id")) else f"#{i}"
        for key in LINEUP_REQUIRED:
            if not is_text(l.get(key)):
                p(f'lineup "{name}": brak pola "{key}"')
        if is_text(l.get("id")):
            if l["id"] in seen:
                p(f'zduplikowane id lineupu "{l["id"]}"')
            seen.add(l["id"])
        if is_text(l.get("side")) and l["side"] not in ("T", "CT"):
            p(f'lineup "{name}": "side" musi być "T" albo "CT"')
        if is_text(l.get("player")) and player_ids is not None and l["player"] not in player_ids:
            p(f'lineup "{name}": nieznany gracz "{l["player"]}"')
        if is_text(l.get("image")) and not is_relative_path(l["image"]):
            p(f'lineup "{name}": ścieżka "image" {RELATIVE_HINT}')
        if is_text(l.get("type")) and l["type"] not in TYPES:
            p(f'lineup "{name}": "type" musi być jednym z: {", ".join(TYPES)}')
        if is_text(l.get("aspect")) and l["aspect"] not in ASPECTS:
            p(f'lineup "{name}": "aspect" musi być jednym z: {", ".join(ASPECTS)}')
        if "resolution" in l:
            p(f'lineup "{name}": pole "resolution" nie jest już używane — użyj "aspect"')
    return out


def image_refs(data):
    """All relative image paths referenced by a map file."""
    refs = []
    if not is_obj(data):
        return refs
    s = data.get("strategies")
    if is_obj(s):
        candidates = [s.get("pistol"), s.get("backup")]
        if is_obj(s.get("execute")):
            candidates += [s["execute"].get("A"), s["execute"].get("B")]
        refs += [st["image"] for st in candidates if is_obj(st) and st.get("image") is not None]
    if isinstance(data.get("lineups"), list):
        refs += [l["image"] for l in data["lineups"] if is_obj(l) and l.get("image") is not None]
    return [r for r in refs if is_relative_path(r)]


def find_exact(root, rel):
    """Return the on-disk relative path (real casing) for rel, or None if it is not a file."""
    cur = Path(root)
    actual = []
    for part in rel.split("/"):
        if part in ("", "."):
            continue
        try:
            entries = os.listdir(cur)
        except OSError:
            return None
        if part in entries:
            name = part
        else:
            name = next((e for e in entries if e.lower() == part.lower()), None)
            if name is None:
                return None
        actual.append(name)
        cur = cur / name
    return "/".join(actual) if cur.is_file() else None


def check_image(root, file, rel, tracked=None):
    actual = find_exact(root, rel)
    if actual is None:
        return [f'{file}: brak pliku obrazka "{rel}"']
    wanted = "/".join(x for x in rel.split("/") if x not in ("", "."))
    if actual != wanted:
        return [
            f'{file}: wielkość liter w "{rel}" nie zgadza się z plikiem "{actual}" '
            "— GitHub Pages rozróżnia wielkość liter"
        ]
    return check_tracked(tracked, file, rel)


def git_tracked(root):
    """Tracked paths (relative to root) when root is inside a git work tree, else None."""
    try:
        inside = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True,
        )
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return None
        listing = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True)
    except OSError:  # git is not installed
        return None
    if listing.returncode != 0:
        return None
    names = listing.stdout.decode("utf-8", errors="replace").split("\0")
    return [n for n in names if n]


def _nfc(text):
    return unicodedata.normalize("NFC", text)


def check_tracked(tracked, file, rel):
    """What GitHub Pages will serve is what git tracks: flag files git does not know under this exact name."""
    if tracked is None:
        return []
    wanted = _nfc("/".join(x for x in rel.split("/") if x not in ("", ".")))
    names = [_nfc(n) for n in tracked]
    if wanted in names:
        return []
    lowered = wanted.lower()
    other = next((n for n in names if n.lower() == lowered), None)
    if other is not None:
        return [
            f'{file}: git zna plik jako "{other}" — zmień nazwę przez: git mv -f "{other}" "{wanted}"'
        ]
    return [f'{file}: plik "{wanted}" nie jest dodany do gita (git add "{wanted}")']


def validate(root):
    root = Path(root)
    problems = []
    tracked = git_tracked(root)
    maps_idx, p = load_json(root, "data/maps.json", tracked)
    problems += p
    team, p = load_json(root, "data/team.json", tracked)
    problems += p
    if maps_idx is not None:
        problems += check_maps_index(maps_idx)
    if team is not None:
        problems += check_team(team)

    map_ids = []
    if is_obj(maps_idx) and isinstance(maps_idx.get("maps"), list):
        map_ids = [m["id"] for m in maps_idx["maps"] if is_obj(m) and is_text(m.get("id"))]
    for mid in map_ids:
        if not MAP_ID_RE.match(mid):
            continue  # already reported; not safe to use as a filename
        rel = f"data/{mid}.json"
        data, p = load_json(root, rel, tracked)
        problems += p
        if data is None:
            continue
        problems += check_map(data, mid, team)
        for img in image_refs(data):
            problems += check_image(root, rel, img, tracked)
    return problems


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    problems = validate(root)
    for line in problems:
        print(line)
    if problems:
        print(f"\n{len(problems)} problem(ów) — popraw je przed pushem.")
        return 1
    print("OK — brak problemów w danych.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
