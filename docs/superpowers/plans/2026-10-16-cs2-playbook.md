# CS2 Team Playbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A static, data-driven CS2 team playbook (one `index.html`) with three strategy slots per map, per-player smoke lineups, and private localStorage notes, deployable to GitHub Pages from a repo subpath.

**Architecture:** `index.html` holds all CSS and two script blocks: `<script id="core">` defines a pure, DOM-free `Core` object (parsing, validation, routing, notes formats) that Node tests load directly from the HTML; the second script is the DOM UI that fetches `data/*.json` with relative URLs and renders views registered in a `VIEWS` table. A stdlib-only `tools/validate.py` checks the same data rules offline plus image existence with exact filename case.

**Tech Stack:** HTML/CSS/vanilla JS (no dependencies), Python 3 stdlib (validator + `unittest`), Node ≥ 20 built-in `node:test` (tests only, never needed by the site).

**Spec:** `docs/superpowers/specs/2026-10-16-cs2-playbook-design.md`

## Global Constraints

- No backend, database, auth, build step, package manager, or external runtime dependency in the site.
- All URLs relative to `index.html`; never a leading `/` (`data/maps.json`, not `/data/maps.json`).
- UI labels in Polish; CS2 terms (smoke, flash, entry, execute, lineup, AWP, T/CT) stay English.
- All user-provided text rendered via `textContent`/text nodes, never `innerHTML`.
- Fixed strategy slots: `pistol`, `execute` (`A`, `B`), `backup`. Content is never copied between A and B.
- localStorage keys: `cs2pb:v1:me`, `cs2pb:v1:notes:<playerId>:<mapId>:<context>`; contexts `map`, `pistol`, `execute-A`, `execute-B`, `backup`, `lineup:<lineupId>`.
- Notes export format: `{ "app": "cs2-playbook", "version": 1, "exportedAt": "<ISO>", "notes": { "<key>": "<text>" } }`, filename `cs2-notatki-YYYY-MM-DD.json`.
- Colours: bg `#16181b`, panel `#1c1f23`, border `#2a2d31`, text `#d7dadf`, muted `#8a9099`, accent `#6a9f5b`, warn `#d29a3a`, err `#d0544f`. No cards, gradients, shadows, animations.
- No browser `alert`/`confirm`/`prompt` dialogs.
- Fetches use `{ cache: "no-cache" }`.
- Example content is marked `"example": true` / "PRZYKŁAD" and contains no real tactics.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Hand-edited JSON with a trailing comma or missing value.** V8 reports these without a position. The user expects "linia X, kolumna Y" anyway. Pinned by `parseJson` tests in Task 3 and `test_syntax_error_reports_line_and_column` in Task 1.
2. **Filename case mismatch** (`Window.png` on disk, `window.png` in JSON). It works on macOS and 404s on GitHub Pages. The validator must flag it. Pinned by `test_image_case_mismatch` in Task 1.
3. **Typing a note, then switching tab, map or player (or closing the page) within the 400 ms debounce.** The text must be saved. Pinned by the flush browser check in Task 5, step 5.
4. **A player removed or renamed in `team.json` while a browser still has the old `cs2pb:v1:me`.** The picker must show "— wybierz —" and nothing may crash. Pinned by `validMe` tests in Task 3.
5. **JSON saved with a UTF-8 BOM** (some Windows editors). It must parse normally. Pinned by BOM tests in Task 1 and Task 3.

---

## File structure

| File | Responsibility | Task |
|---|---|---|
| `tools/validate.py` | Offline data checker (rules + image existence + exact case) | 1 |
| `tools/test_validate.py` | Unit tests for the checker | 1 |
| `data/maps.json`, `data/team.json`, `data/mirage.json` | Example data | 2 |
| `assets/tactics/mirage/*.svg`, `assets/lineups/mirage/<player>/*.svg` | Example placeholder images | 2 |
| `.nojekyll` | Disable Jekyll on GitHub Pages | 2 |
| `index.html` | Whole site: CSS, `Core` script, UI script | 3–7 |
| `tools/test_core.mjs` | Node tests for `Core`, loaded from `index.html` | 3 |
| `README.md` | Polish guide | 8 |

Local preview for all browser checks (run from the repo root; serves the **parent** folder so the site is tested from a subpath):

```bash
python3 -m http.server 8000 --directory "$(dirname "$PWD")"
# open http://localhost:8000/TacticsCS2/
```

---

### Task 1: Data validator (`tools/validate.py`)

**Files:**
- Create: `tools/validate.py`
- Test: `tools/test_validate.py`

**Interfaces:**
- Consumes: nothing.
- Produces: CLI `python3 tools/validate.py [repo_root]` → prints `file: problem` lines, exit 0 (clean) / 1 (problems). Python API `validate(root) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

Create `tools/test_validate.py`:

```python
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate as v  # noqa: E402

VALIDATE = Path(__file__).resolve().parent / "validate.py"

TEAM = {
    "roles": [{"id": "entry", "name": "Entry"}, {"id": "awp", "name": "AWP"}],
    "players": [
        {"id": "p1", "name": "Gracz 1", "role": "entry", "status": "active"},
        {"id": "p2", "name": "Gracz 2", "role": "awp", "status": "active"},
        {"id": "s1", "name": "Rezerwa", "role": None, "status": "sub"},
    ],
}


def strategy(image=None):
    s = {"title": "T", "steps": ["a"], "assignments": [{"role": "entry"}]}
    if image:
        s["image"] = image
    return s


def mirage():
    return {
        "id": "mirage",
        "name": "Mirage",
        "strategies": {
            "pistol": strategy("assets/tactics/mirage/pistol.png"),
            "execute": {"A": strategy(), "B": None},
            "backup": None,
        },
        "lineups": [
            {
                "id": "l1", "player": "p1", "name": "Window", "target": "Mid",
                "side": "T", "resolution": "1920x1080",
                "image": "assets/lineups/mirage/p1/window-1920x1080.png",
            }
        ],
    }


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.write("data/maps.json", {"maps": [{"id": "mirage", "name": "Mirage"}]})
        self.write("data/team.json", TEAM)
        self.write("data/mirage.json", mirage())
        self.write("assets/tactics/mirage/pistol.png", "")
        self.write("assets/lineups/mirage/p1/window-1920x1080.png", "")

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, content):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    def problems(self):
        return v.validate(self.root)

    def assertProblem(self, fragment):
        probs = self.problems()
        self.assertTrue(any(fragment in p for p in probs), f"{fragment!r} not in {probs}")

    def test_valid_repo_has_no_problems(self):
        self.assertEqual(self.problems(), [])

    def test_syntax_error_reports_line_and_column(self):
        self.write("data/team.json", '{\n  "roles": [],\n  "players": [],\n}')
        # Python ≥3.13 points at the comma (3:16); older versions at the brace (4:1).
        probs = self.problems()
        self.assertEqual(len(probs), 1, probs)
        self.assertRegex(probs[0], r"^data/team\.json: błąd składni JSON — linia (3, kolumna 16|4, kolumna 1) ")

    def test_bom_is_accepted(self):
        self.write("data/team.json", "﻿" + json.dumps(TEAM))
        self.assertEqual(self.problems(), [])

    def test_missing_map_file(self):
        self.write("data/maps.json", {"maps": [{"id": "mirage", "name": "Mirage"}, {"id": "dust2", "name": "Dust II"}]})
        self.assertProblem("data/dust2.json: brak pliku")

    def test_bad_map_id(self):
        self.write("data/maps.json", {"maps": [{"id": "Dust 2", "name": "Dust II"}]})
        self.assertProblem('id mapy "Dust 2" może zawierać tylko a-z, 0-9 i -')

    def test_map_id_mismatch(self):
        m = mirage()
        m["id"] = "mirag"
        self.write("data/mirage.json", m)
        self.assertProblem('nie zgadza się z data/maps.json ("mirage")')

    def test_unknown_role_in_assignment(self):
        m = mirage()
        m["strategies"]["execute"]["A"]["assignments"] = [{"role": "lurk"}]
        self.write("data/mirage.json", m)
        self.assertProblem('strategia "execute.A": nieznana rola "lurk" w assignments[0]')

    def test_strategy_without_title(self):
        m = mirage()
        del m["strategies"]["pistol"]["title"]
        self.write("data/mirage.json", m)
        self.assertProblem('strategia "pistol" nie ma "title"')

    def test_unknown_player_in_lineup(self):
        m = mirage()
        m["lineups"][0]["player"] = "p9"
        self.write("data/mirage.json", m)
        self.assertProblem('lineup "l1": nieznany gracz "p9"')

    def test_duplicate_lineup_id(self):
        m = mirage()
        m["lineups"].append(dict(m["lineups"][0]))
        self.write("data/mirage.json", m)
        self.assertProblem('zduplikowane id lineupu "l1"')

    def test_invalid_side_and_resolution(self):
        m = mirage()
        m["lineups"][0]["side"] = "t"
        m["lineups"][0]["resolution"] = "1920×1080"
        self.write("data/mirage.json", m)
        self.assertProblem('lineup "l1": "side" musi być "T" albo "CT"')
        self.assertProblem('lineup "l1": "resolution" w formacie SZEROKOŚĆxWYSOKOŚĆ')

    def test_missing_required_lineup_field(self):
        m = mirage()
        del m["lineups"][0]["target"]
        self.write("data/mirage.json", m)
        self.assertProblem('lineup "l1": brak pola "target"')

    def test_missing_image(self):
        (self.root / "assets/tactics/mirage/pistol.png").unlink()
        self.assertProblem('data/mirage.json: brak pliku obrazka "assets/tactics/mirage/pistol.png"')

    def test_image_case_mismatch(self):
        (self.root / "assets/tactics/mirage/pistol.png").rename(self.root / "assets/tactics/mirage/Pistol.png")
        self.assertProblem('wielkość liter w "assets/tactics/mirage/pistol.png" nie zgadza się z plikiem "assets/tactics/mirage/Pistol.png"')

    def test_absolute_image_path_rejected(self):
        m = mirage()
        m["lineups"][0]["image"] = "/assets/x.png"
        self.write("data/mirage.json", m)
        self.assertProblem('lineup "l1": ścieżka "image" musi być względna')

    def test_two_active_players_same_role(self):
        team = json.loads(json.dumps(TEAM))
        team["players"][1]["role"] = "entry"
        self.write("data/team.json", team)
        self.assertProblem('rola "entry" ma kilku aktywnych graczy: p1, p2')

    def test_unknown_player_role_and_bad_status(self):
        team = json.loads(json.dumps(TEAM))
        team["players"][2]["role"] = "igl"
        team["players"][2]["status"] = "bench"
        self.write("data/team.json", team)
        self.assertProblem('gracz "s1": nieznana rola "igl"')
        self.assertProblem('gracz "s1": "status" musi być "active" albo "sub"')

    def test_cli_exit_codes(self):
        ok = subprocess.run([sys.executable, str(VALIDATE), str(self.root)], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        (self.root / "assets/tactics/mirage/pistol.png").unlink()
        bad = subprocess.run([sys.executable, str(VALIDATE), str(self.root)], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("brak pliku obrazka", bad.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tools/test_validate.py -v`
Expected: ERROR `ModuleNotFoundError: No module named 'validate'`.

- [ ] **Step 3: Implement `tools/validate.py`**

```python
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
import sys
from pathlib import Path

MAP_ID_RE = re.compile(r"^[a-z0-9-]+$")
RES_RE = re.compile(r"^\d+x\d+$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
LINEUP_REQUIRED = ("id", "player", "name", "target", "side", "resolution", "image")
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


def load_json(root, rel):
    """Return (data, problems). data is None when the file is missing or invalid."""
    path = Path(root) / rel
    if not path.is_file():
        return None, [f"{rel}: brak pliku"]
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return json.load(fh), []
    except json.JSONDecodeError as e:
        return None, [f"{rel}: błąd składni JSON — linia {e.lineno}, kolumna {e.colno} ({e.msg})"]
    except UnicodeDecodeError:
        return None, [f"{rel}: plik nie jest zapisany w UTF-8"]


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
    return out


def team_ids(team, key):
    if not is_obj(team) or not isinstance(team.get(key), list):
        return set()
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
        if not isinstance(role, str) or role not in role_ids:
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
        check_strategy(s.get("pistol"), "pistol", role_ids, p)
        check_strategy(s.get("backup"), "backup", role_ids, p)
        ex = s.get("execute")
        if ex is not None and not is_obj(ex):
            p('"strategies.execute" musi być obiektem z kluczami "A" i "B"')
        elif is_obj(ex):
            for variant in ("A", "B"):
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
        if is_text(l.get("player")) and l["player"] not in player_ids:
            p(f'lineup "{name}": nieznany gracz "{l["player"]}"')
        if is_text(l.get("image")) and not is_relative_path(l["image"]):
            p(f'lineup "{name}": ścieżka "image" {RELATIVE_HINT}')
        if is_text(l.get("resolution")) and not RES_RE.match(l["resolution"]):
            p(f'lineup "{name}": "resolution" w formacie SZEROKOŚĆxWYSOKOŚĆ, np. 1920x1080')
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


def check_image(root, file, rel):
    actual = find_exact(root, rel)
    if actual is None:
        return [f'{file}: brak pliku obrazka "{rel}"']
    wanted = "/".join(x for x in rel.split("/") if x not in ("", "."))
    if actual != wanted:
        return [
            f'{file}: wielkość liter w "{rel}" nie zgadza się z plikiem "{actual}" '
            "— GitHub Pages rozróżnia wielkość liter"
        ]
    return []


def validate(root):
    root = Path(root)
    problems = []
    maps_idx, p = load_json(root, "data/maps.json")
    problems += p
    team, p = load_json(root, "data/team.json")
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
        data, p = load_json(root, rel)
        problems += p
        if data is None:
            continue
        problems += check_map(data, mid, team)
        for img in image_refs(data):
            problems += check_image(root, rel, img)
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tools/test_validate.py -v`
Expected: all 18 tests `ok`.

- [ ] **Step 5: Commit**

```bash
git add tools/validate.py tools/test_validate.py
git commit -m "Add offline data validator with exact-case image checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Example data, placeholder images, `.nojekyll`

**Files:**
- Create: `data/maps.json`, `data/team.json`, `data/mirage.json`, `.nojekyll`
- Create (generated): `assets/tactics/mirage/pistol.svg`, `execute-a.svg`, `backup.svg`; `assets/lineups/mirage/p1/example-smoke-1-1920x1080.svg`, `assets/lineups/mirage/p1/example-smoke-2-2560x1440.svg`, `assets/lineups/mirage/p2/example-smoke-3-1280x960.svg`

**Interfaces:**
- Consumes: `tools/validate.py` (Task 1).
- Produces: example data that later tasks render. Player ids `p1`–`p5`, `s1`; role ids `entry`, `second`, `support`, `lurk`, `awp`; map id `mirage`; Execute B is `null`; lineups `example-smoke-1` (p1, T, 1920x1080), `example-smoke-2` (p1, T, 2560x1440), `example-smoke-3` (p2, CT, 1280x960).

- [ ] **Step 1: Confirm the validator fails on an empty repo**

Run: `python3 tools/validate.py`
Expected: exit 1, lines `data/maps.json: brak pliku` and `data/team.json: brak pliku`.

- [ ] **Step 2: Create `data/maps.json`**

```json
{
  "maps": [
    { "id": "mirage", "name": "Mirage" }
  ]
}
```

- [ ] **Step 3: Create `data/team.json`**

```json
{
  "roles": [
    { "id": "entry",   "name": "Entry" },
    { "id": "second",  "name": "Second entry" },
    { "id": "support", "name": "Support" },
    { "id": "lurk",    "name": "Lurk" },
    { "id": "awp",     "name": "AWP" }
  ],
  "players": [
    { "id": "p1", "name": "PRZYKŁAD Gracz 1",   "role": "entry",   "status": "active" },
    { "id": "p2", "name": "PRZYKŁAD Gracz 2",   "role": "second",  "status": "active" },
    { "id": "p3", "name": "PRZYKŁAD Gracz 3",   "role": "support", "status": "active" },
    { "id": "p4", "name": "PRZYKŁAD Gracz 4",   "role": "lurk",    "status": "active" },
    { "id": "p5", "name": "PRZYKŁAD Gracz 5",   "role": "awp",     "status": "active" },
    { "id": "s1", "name": "PRZYKŁAD Rezerwa 1", "role": null,      "status": "sub" }
  ]
}
```

- [ ] **Step 4: Create `data/mirage.json`**

```json
{
  "id": "mirage",
  "name": "Mirage",
  "strategies": {
    "pistol": {
      "example": true,
      "title": "PRZYKŁAD — pistolówka (podmień na własną)",
      "summary": "To jest przykładowy wpis, który pokazuje format danych. To NIE jest taktyka zespołu.\nZastąp tytuł, opis, obrazek, kroki i tabelę własną strategią w data/mirage.json.",
      "image": "assets/tactics/mirage/pistol.svg",
      "steps": [
        "Krok 1 — opisz, co robicie na starcie rundy.",
        "Krok 2 — opisz moment wejścia lub zmiany.",
        "Krok 3 — opisz plan po zdobyciu lub utracie przewagi."
      ],
      "assignments": [
        { "role": "entry",   "position": "np. pozycja startowa", "utility": "np. flash", "action": "opis zadania", "timing": "np. 0:10", "notes": "" },
        { "role": "second",  "position": "np. pozycja startowa", "utility": "np. smoke", "action": "opis zadania", "timing": "po wejściu entry", "notes": "" },
        { "role": "support", "position": "np. pozycja startowa", "utility": "np. smoke", "action": "opis zadania", "timing": "", "notes": "" },
        { "role": "lurk",    "position": "np. pozycja startowa", "utility": "", "action": "opis zadania", "timing": "", "notes": "" },
        { "role": "awp",     "position": "np. pozycja startowa", "utility": "", "action": "opis zadania", "timing": "", "notes": "" }
      ],
      "notes": "Miejsce na wspólne notatki zespołu do tej strategii."
    },
    "execute": {
      "A": {
        "example": true,
        "title": "PRZYKŁAD — execute A (podmień na własny)",
        "summary": "Przykładowy wpis execute na bombsite A. To NIE jest taktyka zespołu.",
        "image": "assets/tactics/mirage/execute-a.svg",
        "steps": [
          "Krok 1 — ustawienie przed executem.",
          "Krok 2 — utility (kolejność smoke'ów i flashy).",
          "Krok 3 — kolejność wejścia i trade'y.",
          "Krok 4 — plant i ustawienie po plancie."
        ],
        "assignments": [
          { "role": "entry",   "position": "np. pozycja", "utility": "np. 2× flash", "action": "pierwszy na site", "timing": "1.", "notes": "trade: second" },
          { "role": "second",  "position": "np. pozycja", "utility": "np. smoke", "action": "drugi na site", "timing": "2.", "notes": "" },
          { "role": "support", "position": "np. pozycja", "utility": "np. smoke + molotov", "action": "utility z daleka", "timing": "przed wejściem", "notes": "" },
          { "role": "lurk",    "position": "np. pozycja", "utility": "", "action": "kontrola rotacji", "timing": "", "notes": "" },
          { "role": "awp",     "position": "np. pozycja", "utility": "np. flash", "action": "pick przed executem", "timing": "", "notes": "" }
        ],
        "notes": ""
      },
      "B": null
    },
    "backup": {
      "example": true,
      "title": "PRZYKŁAD — backup (podmień na własny)",
      "summary": "Przykładowa strategia awaryjna. Obrazek to wcześniej narysowany diagram (np. z Excalidraw lub Painta), zapisany jako PNG.",
      "image": "assets/tactics/mirage/backup.svg",
      "steps": [],
      "assignments": [
        { "role": "entry", "position": "np. pozycja", "utility": "", "action": "opis zadania", "timing": "", "notes": "" },
        { "role": "awp",   "position": "np. pozycja", "utility": "", "action": "opis zadania", "timing": "", "notes": "" }
      ],
      "notes": ""
    }
  },
  "lineups": [
    {
      "id": "example-smoke-1",
      "example": true,
      "player": "p1",
      "name": "PRZYKŁAD smoke 1",
      "target": "np. Window",
      "side": "T",
      "from": "np. T spawn",
      "throw": "np. jumpthrow",
      "resolution": "1920x1080",
      "aspect": "16:9",
      "image": "assets/lineups/mirage/p1/example-smoke-1-1920x1080.svg",
      "instructions": "Opisz, gdzie stanąć i gdzie celować.",
      "notes": ""
    },
    {
      "id": "example-smoke-2",
      "example": true,
      "player": "p1",
      "name": "PRZYKŁAD smoke 2",
      "target": "np. CT",
      "side": "T",
      "from": "np. T ramp",
      "throw": "np. lewy przycisk",
      "resolution": "2560x1440",
      "aspect": "16:9",
      "image": "assets/lineups/mirage/p1/example-smoke-2-2560x1440.svg",
      "instructions": "",
      "notes": ""
    },
    {
      "id": "example-smoke-3",
      "example": true,
      "player": "p2",
      "name": "PRZYKŁAD smoke 3",
      "target": "np. Top mid",
      "side": "CT",
      "from": "np. CT spawn",
      "resolution": "1280x960",
      "aspect": "4:3",
      "image": "assets/lineups/mirage/p2/example-smoke-3-1280x960.svg",
      "instructions": "Lineup dla 4:3 — na 16:9 nie zadziała tak samo.",
      "notes": ""
    }
  ]
}
```

- [ ] **Step 5: Run the validator to confirm it reports the missing images**

Run: `python3 tools/validate.py`
Expected: exit 1 with six `brak pliku obrazka` lines (data is valid, images not yet created).

- [ ] **Step 6: Generate placeholder SVGs and `.nojekyll`**

Run from the repo root (one-off generator, not committed):

```bash
python3 - <<'EOF'
from pathlib import Path
from xml.sax.saxutils import escape

items = [
    ("assets/tactics/mirage/pistol.svg", 1600, 900, "Pistolówka", "podmień na własny screenshot lub diagram"),
    ("assets/tactics/mirage/execute-a.svg", 1600, 900, "Execute A", "podmień na własny screenshot lub diagram"),
    ("assets/tactics/mirage/backup.svg", 1600, 900, "Backup", "podmień na wcześniej narysowany diagram"),
    ("assets/lineups/mirage/p1/example-smoke-1-1920x1080.svg", 1920, 1080, "Lineup · 1920×1080 · 16:9", "podmień na screenshot z gry"),
    ("assets/lineups/mirage/p1/example-smoke-2-2560x1440.svg", 2560, 1440, "Lineup · 2560×1440 · 16:9", "podmień na screenshot z gry"),
    ("assets/lineups/mirage/p2/example-smoke-3-1280x960.svg", 1280, 960, "Lineup · 1280×960 · 4:3", "podmień na screenshot z gry"),
]
for rel, w, h, title, sub in items:
    fs = w // 25
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
        f'  <rect width="{w}" height="{h}" fill="#202327"/>\n'
        f'  <rect x="6" y="6" width="{w - 12}" height="{h - 12}" fill="none" stroke="#d29a3a" stroke-width="6" stroke-dasharray="30 20"/>\n'
        f'  <text x="{w // 2}" y="{h // 2 - fs}" fill="#d29a3a" font-family="sans-serif" font-size="{fs * 2}" font-weight="700" text-anchor="middle">PRZYKŁAD</text>\n'
        f'  <text x="{w // 2}" y="{h // 2 + fs}" fill="#d7dadf" font-family="sans-serif" font-size="{fs}" text-anchor="middle">{escape(title)}</text>\n'
        f'  <text x="{w // 2}" y="{h // 2 + int(fs * 2.4)}" fill="#8a9099" font-family="sans-serif" font-size="{int(fs * 0.7)}" text-anchor="middle">{escape(sub)}</text>\n'
        f'</svg>\n'
    )
    p = Path(rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(svg, encoding="utf-8")
    print("wrote", rel)
EOF
touch .nojekyll
```

Expected: six `wrote …` lines.

- [ ] **Step 7: Run the validator to verify it passes**

Run: `python3 tools/validate.py`
Expected: `OK — brak problemów w danych.`, exit 0.

- [ ] **Step 8: Commit**

```bash
git add data assets .nojekyll
git commit -m "Add example Mirage data and placeholder images

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `index.html` skeleton and the pure `Core` module

**Files:**
- Create: `index.html`
- Test: `tools/test_core.mjs`

**Interfaces:**
- Consumes: nothing at runtime.
- Produces: global `Core` with these exact members (used by Tasks 4–7):
  - Constants: `NOTE_PREFIX = "cs2pb:v1:notes:"`, `ME_KEY = "cs2pb:v1:me"`, `TABS = ["pistolowka","execute","backup","lineupy","notatki"]`.
  - `parseJson(text: string, path: string) → any` (throws `Error("<path>: błąd składni JSON — linia L, kolumna C")`).
  - `plural(n, one, few, many) → string`.
  - `normalizeTeam(team) → { roles: Role[], players: Player[] }`; `normalizeMap(data) → { name, strategies: { pistol, backup, execute: { A, B } }, lineups }` (strategies are `null` or objects with array `steps` and `assignments`).
  - `checkMapsIndex(data) / checkTeam(team) / checkMap(data, mapId, team) → { file, message }[]`.
  - `resolveRole(team, roleId) → { kind: "active"|"sub"|"none", players: Player[] }`.
  - `groupPlayers(team) → { active: Player[], subs: Player[] }`; `validMe(id, team) → string|null`; `defaultLineupPlayer(team, meId) → string|null`.
  - `parseHash(hash, { mapIds, playerIds }) → { map, tab, variant, player }`; `buildHash(state) → string`.
  - `noteKey(playerId, mapId, context) → string`; `noteContext(tab, variant) → string`.
  - `buildNotesExport(entries: [key, value][], date) → object`; `parseNotesImport(text) → { ok: true, notes } | { ok: false, error }`; `exportFilename(date) → string`.
  - `formatResolution(res) → string`; `lineupFacets(lineups) → { sides, resolutions }`; `filterLineups(lineups, { side, resolution }) → Lineup[]`.

- [ ] **Step 1: Create the `index.html` skeleton with an empty `Core`**

```html
<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>CS2 Playbook</title>
</head>
<body>
<script id="core">
const Core = (() => {
  "use strict";
  return {};
})();
</script>
</body>
</html>
```

- [ ] **Step 2: Write the failing tests**

Create `tools/test_core.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const match = html.match(/<script id="core">([\s\S]*?)<\/script>/);
assert.ok(match, 'index.html must contain <script id="core">');
const Core = new Function(`${match[1]}\nreturn Core;`)();

const TEAM = Core.normalizeTeam({
  roles: [{ id: "entry", name: "Entry" }, { id: "awp", name: "AWP" }, { id: "lurk", name: "Lurk" }],
  players: [
    { id: "p1", name: "A", role: "entry", status: "active" },
    { id: "p2", name: "B", role: "awp", status: "active" },
    { id: "s1", name: "S", role: "lurk", status: "sub" },
    { id: "s2", name: "T", role: null, status: "sub" },
  ],
});

test("parseJson parses valid JSON and strips a BOM", () => {
  assert.deepEqual(Core.parseJson('{"a":1}', "x.json"), { a: 1 });
  assert.deepEqual(Core.parseJson('﻿{"a":1}', "x.json"), { a: 1 });
});

test("parseJson reports line and column for a missing value", () => {
  assert.throws(() => Core.parseJson('{\n  "a": 1,\n  "b": \n}', "data/x.json"),
    { message: "data/x.json: błąd składni JSON — linia 4, kolumna 1" });
});

test("parseJson reports line and column for a trailing comma", () => {
  assert.throws(() => Core.parseJson('{\n  "a": [1, 2,],\n}', "data/x.json"),
    { message: "data/x.json: błąd składni JSON — linia 2, kolumna 14" });
});

test("parseJson reports a missing comma and an empty file", () => {
  assert.throws(() => Core.parseJson('{\n  "a": 1\n  "b": 2\n}', "f.json"),
    { message: "f.json: błąd składni JSON — linia 3, kolumna 3" });
  assert.throws(() => Core.parseJson("", "f.json"),
    { message: "f.json: błąd składni JSON — linia 1, kolumna 1" });
});

test("plural follows Polish rules", () => {
  const f = (n) => Core.plural(n, "problem", "problemy", "problemów");
  assert.deepEqual([1, 2, 4, 5, 12, 14, 22, 25].map(f),
    ["problem", "problemy", "problemy", "problemów", "problemów", "problemów", "problemy", "problemów"]);
});

test("normalizeTeam tolerates bad input", () => {
  assert.deepEqual(Core.normalizeTeam(null), { roles: [], players: [] });
  assert.deepEqual(Core.normalizeTeam({ roles: [{ id: "a" }, 5, {}], players: "x" }), { roles: [{ id: "a" }], players: [] });
});

test("normalizeMap fills missing slots with null and arrays with []", () => {
  const m = Core.normalizeMap({ name: "M", strategies: { pistol: { title: "P" } }, lineups: "nope" });
  assert.equal(m.strategies.pistol.title, "P");
  assert.deepEqual(m.strategies.pistol.steps, []);
  assert.deepEqual(m.strategies.pistol.assignments, []);
  assert.equal(m.strategies.backup, null);
  assert.deepEqual(m.strategies.execute, { A: null, B: null });
  assert.deepEqual(m.lineups, []);
});

test("resolveRole prefers active, falls back to sub, else none", () => {
  assert.deepEqual(Core.resolveRole(TEAM, "entry").kind, "active");
  assert.deepEqual(Core.resolveRole(TEAM, "entry").players.map((p) => p.id), ["p1"]);
  assert.deepEqual(Core.resolveRole(TEAM, "lurk").kind, "sub");
  assert.deepEqual(Core.resolveRole(TEAM, "support"), { kind: "none", players: [] });
});

test("groupPlayers, validMe, defaultLineupPlayer", () => {
  const g = Core.groupPlayers(TEAM);
  assert.deepEqual(g.active.map((p) => p.id), ["p1", "p2"]);
  assert.deepEqual(g.subs.map((p) => p.id), ["s1", "s2"]);
  assert.equal(Core.validMe("s2", TEAM), "s2");
  assert.equal(Core.validMe("gone", TEAM), null);
  assert.equal(Core.validMe(null, TEAM), null);
  assert.equal(Core.defaultLineupPlayer(TEAM, "s1"), "s1");
  assert.equal(Core.defaultLineupPlayer(TEAM, "gone"), "p1");
  assert.equal(Core.defaultLineupPlayer(Core.normalizeTeam({ roles: [], players: [] }), null), null);
});

test("checkTeam flags bad roles, statuses and shared roles", () => {
  const msgs = Core.checkTeam({
    roles: [{ id: "entry", name: "Entry" }],
    players: [
      { id: "p1", name: "A", role: "entry", status: "active" },
      { id: "p2", name: "B", role: "entry", status: "active" },
      { id: "p3", name: "C", role: "igl", status: "bench" },
    ],
  }).map((p) => p.message);
  assert.ok(msgs.includes('rola "entry" ma kilku aktywnych graczy: p1, p2'));
  assert.ok(msgs.includes('gracz "p3": nieznana rola "igl"'));
  assert.ok(msgs.includes('gracz "p3": "status" musi być "active" albo "sub"'));
  assert.deepEqual(Core.checkTeam([]).map((p) => p.message), ['oczekiwano obiektu z listami "roles" i "players"']);
});

test("checkMapsIndex flags bad ids", () => {
  const msgs = Core.checkMapsIndex({ maps: [{ id: "Dust 2", name: "D" }, { id: "a", name: "A" }, { id: "a", name: "A" }] }).map((p) => p.message);
  assert.ok(msgs.includes('id mapy "Dust 2" może zawierać tylko a-z, 0-9 i -'));
  assert.ok(msgs.includes('zduplikowane id mapy "a"'));
});

test("checkMap flags references and formats", () => {
  const data = {
    id: "mirag",
    strategies: {
      pistol: { title: "P", assignments: [{ role: "support" }] },
      execute: { A: null, B: { steps: "x" } },
      backup: null,
    },
    lineups: [
      { id: "l1", player: "p9", name: "N", target: "T", side: "t", resolution: "1920×1080", image: "/abs.png" },
      { id: "l1", player: "p1", name: "N", side: "T", resolution: "1920x1080", image: "a.png" },
    ],
  };
  const out = Core.checkMap(data, "mirage", TEAM);
  assert.ok(out.every((p) => p.file === "data/mirage.json"));
  const msgs = out.map((p) => p.message);
  for (const expected of [
    '"id" w pliku ("mirag") nie zgadza się z data/maps.json ("mirage")',
    'strategia "pistol": nieznana rola "support" w assignments[0]',
    'strategia "execute.B" nie ma "title"',
    'strategia "execute.B": "steps" musi być listą tekstów',
    'lineup "l1": nieznany gracz "p9"',
    'lineup "l1": "side" musi być "T" albo "CT"',
    'lineup "l1": "resolution" w formacie SZEROKOŚĆxWYSOKOŚĆ, np. 1920x1080',
    'lineup "l1": ścieżka "image" musi być względna (bez / na początku, bez .., bez http)',
    'zduplikowane id lineupu "l1"',
    'lineup "l1": brak pola "target"',
  ]) assert.ok(msgs.includes(expected), `missing: ${expected}\n got: ${msgs.join("\n")}`);
});

test("parseHash defaults and validates every part", () => {
  const ctx = { mapIds: ["mirage", "dust2"], playerIds: ["p1", "s1"] };
  assert.deepEqual(Core.parseHash("", ctx), { map: "mirage", tab: "pistolowka", variant: "A", player: null });
  assert.deepEqual(Core.parseHash("#nuke/whatever", ctx), { map: "mirage", tab: "pistolowka", variant: "A", player: null });
  assert.deepEqual(Core.parseHash("#dust2/execute/b", ctx), { map: "dust2", tab: "execute", variant: "B", player: null });
  assert.deepEqual(Core.parseHash("#dust2/execute/x", ctx).variant, "A");
  assert.deepEqual(Core.parseHash("#mirage/lineupy/s1", ctx).player, "s1");
  assert.deepEqual(Core.parseHash("#mirage/lineupy/ghost", ctx).player, null);
  assert.deepEqual(Core.parseHash("#mirage/%E0%A4%A", ctx).tab, "pistolowka");
});

test("buildHash round-trips through parseHash", () => {
  const ctx = { mapIds: ["mirage"], playerIds: ["p1"] };
  assert.equal(Core.buildHash({ map: "mirage", tab: "execute", variant: "B", player: null }), "#mirage/execute/B");
  assert.equal(Core.buildHash({ map: "mirage", tab: "lineupy", variant: "A", player: "p1" }), "#mirage/lineupy/p1");
  assert.equal(Core.buildHash({ map: "mirage", tab: "lineupy", variant: "A", player: null }), "#mirage/lineupy");
  assert.equal(Core.buildHash({ map: "mirage", tab: "backup", variant: "B", player: "p1" }), "#mirage/backup");
  for (const h of ["#mirage/execute/B", "#mirage/lineupy/p1", "#mirage/notatki"]) {
    assert.equal(Core.buildHash(Core.parseHash(h, ctx)), h);
  }
});

test("noteKey and noteContext", () => {
  assert.equal(Core.noteKey("p1", "mirage", "execute-B"), "cs2pb:v1:notes:p1:mirage:execute-B");
  assert.equal(Core.noteContext("pistolowka", "A"), "pistol");
  assert.equal(Core.noteContext("execute", "B"), "execute-B");
  assert.equal(Core.noteContext("backup", "A"), "backup");
  assert.equal(Core.noteContext("notatki", "A"), "map");
});

test("notes export/import round-trip", () => {
  const date = new Date(Date.UTC(2026, 9, 16, 12, 0, 0));
  const exp = Core.buildNotesExport([["cs2pb:v1:notes:p1:mirage:map", "hej"], ["other", "x"]], date);
  assert.deepEqual(exp, { app: "cs2-playbook", version: 1, exportedAt: "2026-10-16T12:00:00.000Z", notes: { "cs2pb:v1:notes:p1:mirage:map": "hej" } });
  assert.deepEqual(Core.parseNotesImport(JSON.stringify(exp)), { ok: true, notes: exp.notes });
});

test("parseNotesImport rejects bad files with a reason", () => {
  assert.equal(Core.parseNotesImport("{oops").error, "Plik nie jest poprawnym JSON-em.");
  assert.equal(Core.parseNotesImport('{"app":"x","version":1,"notes":{}}').error, "To nie jest plik eksportu notatek CS2 Playbook (wersja 1).");
  assert.equal(Core.parseNotesImport('{"app":"cs2-playbook","version":1,"notes":{"evil":"x"}}').error, "Nieprawidłowy klucz notatki: evil");
  assert.equal(Core.parseNotesImport('{"app":"cs2-playbook","version":1,"notes":{"cs2pb:v1:notes:a:b:map":5}}').error, "Notatka cs2pb:v1:notes:a:b:map nie jest tekstem.");
});

test("exportFilename uses the local date", () => {
  assert.equal(Core.exportFilename(new Date(2026, 2, 5, 23, 59)), "cs2-notatki-2026-03-05.json");
});

test("formatResolution, lineupFacets, filterLineups", () => {
  assert.equal(Core.formatResolution("1920x1080"), "1920×1080");
  assert.equal(Core.formatResolution(""), "?");
  const ls = [
    { id: "a", side: "T", resolution: "2560x1440" },
    { id: "b", side: "CT", resolution: "1920x1080" },
    { id: "c", side: "T", resolution: "1920x1080" },
  ];
  assert.deepEqual(Core.lineupFacets(ls), { sides: ["CT", "T"], resolutions: ["1920x1080", "2560x1440"] });
  assert.deepEqual(Core.filterLineups(ls, { side: "T", resolution: null }).map((l) => l.id), ["a", "c"]);
  assert.deepEqual(Core.filterLineups(ls, { side: null, resolution: "1920x1080" }).map((l) => l.id), ["b", "c"]);
  assert.deepEqual(Core.filterLineups(ls, { side: "T", resolution: "1920x1080" }).map((l) => l.id), ["c"]);
});
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `node --test tools/test_core.mjs`
Expected: FAIL, e.g. `TypeError: Core.normalizeTeam is not a function`.

- [ ] **Step 4: Implement `Core`**

Replace the whole `<script id="core">…</script>` block in `index.html` with:

```html
<script id="core">
// Pure logic, no DOM. Loaded by tools/test_core.mjs for unit tests.
const Core = (() => {
  "use strict";
  const NOTE_PREFIX = "cs2pb:v1:notes:";
  const ME_KEY = "cs2pb:v1:me";
  const TABS = ["pistolowka", "execute", "backup", "lineupy", "notatki"];
  const VARIANTS = ["A", "B"];
  const MAP_ID_RE = /^[a-z0-9-]+$/;
  const RES_RE = /^\d+x\d+$/;
  const LINEUP_REQUIRED = ["id", "player", "name", "target", "side", "resolution", "image"];
  const RELATIVE_HINT = "musi być względna (bez / na początku, bez .., bez http)";

  const isObj = (x) => x !== null && typeof x === "object" && !Array.isArray(x);
  const arr = (x) => (Array.isArray(x) ? x : []);
  const isText = (x) => typeof x === "string" && x.trim() !== "";
  const isRelativePath = (x) =>
    isText(x) && !x.startsWith("/") && !/^[A-Za-z][A-Za-z0-9+.-]*:/.test(x) && !x.split("/").includes("..");

  // ── JSON with reliable error positions (V8 omits them for some errors) ──
  function findJsonErrorOffset(text) {
    let i = 0;
    const fail = () => { throw i; };
    const ws = () => { while (i < text.length && " \t\n\r".includes(text[i])) i++; };
    function value() {
      ws();
      const c = text[i];
      if (c === "{") return object();
      if (c === "[") return array();
      if (c === '"') return string();
      if (c === "-" || (c >= "0" && c <= "9")) return number();
      for (const lit of ["true", "false", "null"]) {
        if (text.startsWith(lit, i)) { i += lit.length; return; }
      }
      fail();
    }
    function object() {
      i++; ws();
      if (text[i] === "}") { i++; return; }
      for (;;) {
        ws();
        if (text[i] !== '"') fail();
        string(); ws();
        if (text[i] !== ":") fail();
        i++;
        value(); ws();
        if (text[i] === ",") { i++; continue; }
        if (text[i] === "}") { i++; return; }
        fail();
      }
    }
    function array() {
      i++; ws();
      if (text[i] === "]") { i++; return; }
      for (;;) {
        value(); ws();
        if (text[i] === ",") { i++; continue; }
        if (text[i] === "]") { i++; return; }
        fail();
      }
    }
    function string() {
      i++;
      while (i < text.length) {
        const c = text[i];
        if (c === '"') { i++; return; }
        if (c === "\\") { i += 2; continue; }
        if (c < " ") fail();
        i++;
      }
      fail();
    }
    function number() {
      const m = /^-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?/.exec(text.slice(i));
      if (!m) fail();
      i += m[0].length;
    }
    try {
      value(); ws();
      if (i < text.length) fail();
      return null;
    } catch (pos) {
      if (typeof pos === "number") return pos;
      throw pos;
    }
  }

  function parseJson(text, path) {
    const clean = String(text).replace(/^﻿/, "");
    try {
      return JSON.parse(clean);
    } catch {
      const offset = findJsonErrorOffset(clean);
      let where = "";
      if (offset !== null) {
        const lines = clean.slice(0, offset).split("\n");
        where = ` — linia ${lines.length}, kolumna ${lines[lines.length - 1].length + 1}`;
      }
      throw new Error(`${path}: błąd składni JSON${where}`);
    }
  }

  function plural(n, one, few, many) {
    if (n === 1) return one;
    const d = n % 10, dd = n % 100;
    return d >= 2 && d <= 4 && !(dd >= 12 && dd <= 14) ? few : many;
  }

  // ── normalisation: shapes the UI can rely on ──
  function normalizeTeam(team) {
    const t = isObj(team) ? team : {};
    return {
      roles: arr(t.roles).filter((r) => isObj(r) && isText(r.id)),
      players: arr(t.players).filter((p) => isObj(p) && isText(p.id)),
    };
  }

  function normalizeStrategy(s) {
    if (!isObj(s)) return null;
    return {
      ...s,
      steps: arr(s.steps).filter((x) => typeof x === "string"),
      assignments: arr(s.assignments).filter(isObj),
    };
  }

  function normalizeMap(data) {
    const d = isObj(data) ? data : {};
    const s = isObj(d.strategies) ? d.strategies : {};
    const ex = isObj(s.execute) ? s.execute : {};
    return {
      name: d.name,
      strategies: {
        pistol: normalizeStrategy(s.pistol),
        backup: normalizeStrategy(s.backup),
        execute: { A: normalizeStrategy(ex.A), B: normalizeStrategy(ex.B) },
      },
      lineups: arr(d.lineups).filter((l) => isObj(l) && isText(l.id)),
    };
  }

  // ── data checks (mirrors tools/validate.py, minus file existence) ──
  function checkMapsIndex(data) {
    const file = "data/maps.json";
    const out = [];
    const p = (message) => out.push({ file, message });
    if (!isObj(data) || !Array.isArray(data.maps)) { p('oczekiwano obiektu z listą "maps"'); return out; }
    const seen = new Set();
    data.maps.forEach((m, i) => {
      if (!isObj(m) || !isText(m.id)) return p(`maps[${i}] musi mieć "id" (tekst)`);
      if (!MAP_ID_RE.test(m.id)) p(`id mapy "${m.id}" może zawierać tylko a-z, 0-9 i -`);
      if (seen.has(m.id)) p(`zduplikowane id mapy "${m.id}"`);
      seen.add(m.id);
      if (!isText(m.name)) p(`mapa "${m.id}" nie ma "name"`);
    });
    return out;
  }

  function checkTeam(team) {
    const file = "data/team.json";
    const out = [];
    const p = (message) => out.push({ file, message });
    if (!isObj(team)) { p('oczekiwano obiektu z listami "roles" i "players"'); return out; }
    if (!Array.isArray(team.roles)) p('brak listy "roles"');
    if (!Array.isArray(team.players)) p('brak listy "players"');
    const roleIds = new Set();
    arr(team.roles).forEach((r, i) => {
      if (!isObj(r) || !isText(r.id)) return p(`roles[${i}] musi mieć "id" (tekst)`);
      if (roleIds.has(r.id)) p(`zduplikowane id roli "${r.id}"`);
      roleIds.add(r.id);
      if (!isText(r.name)) p(`rola "${r.id}" nie ma "name"`);
    });
    const playerIds = new Set();
    const holders = new Map(); // roleId -> { active: [], sub: [] }
    arr(team.players).forEach((pl, i) => {
      if (!isObj(pl) || !isText(pl.id)) return p(`players[${i}] musi mieć "id" (tekst)`);
      if (playerIds.has(pl.id)) p(`zduplikowane id gracza "${pl.id}"`);
      playerIds.add(pl.id);
      if (!isText(pl.name)) p(`gracz "${pl.id}" nie ma "name"`);
      const statusOk = pl.status === "active" || pl.status === "sub";
      if (!statusOk) p(`gracz "${pl.id}": "status" musi być "active" albo "sub"`);
      if (pl.role == null) return;
      if (typeof pl.role !== "string" || !roleIds.has(pl.role)) return p(`gracz "${pl.id}": nieznana rola "${pl.role}"`);
      if (!statusOk) return;
      if (!holders.has(pl.role)) holders.set(pl.role, { active: [], sub: [] });
      holders.get(pl.role)[pl.status].push(pl.id);
    });
    for (const [role, h] of holders) {
      if (h.active.length > 1) p(`rola "${role}" ma kilku aktywnych graczy: ${h.active.join(", ")}`);
      if (h.sub.length > 1) p(`rola "${role}" ma kilku rezerwowych: ${h.sub.join(", ")}`);
    }
    return out;
  }

  function checkStrategy(st, label, roleIds, p) {
    if (st == null) return;
    if (!isObj(st)) return p(`strategia "${label}" musi być obiektem albo null`);
    if (!isText(st.title)) p(`strategia "${label}" nie ma "title"`);
    if (st.image != null && !isRelativePath(st.image)) p(`strategia "${label}": ścieżka "image" ${RELATIVE_HINT}`);
    if (st.steps != null && !(Array.isArray(st.steps) && st.steps.every((s) => typeof s === "string"))) {
      p(`strategia "${label}": "steps" musi być listą tekstów`);
    }
    if (st.assignments == null) return;
    if (!Array.isArray(st.assignments)) return p(`strategia "${label}": "assignments" musi być listą`);
    st.assignments.forEach((a, i) => {
      const role = isObj(a) ? a.role : undefined;
      if (typeof role !== "string" || !roleIds.has(role)) {
        p(`strategia "${label}": nieznana rola "${role ?? ""}" w assignments[${i}]`);
      }
    });
  }

  function checkMap(data, mapId, team) {
    const file = `data/${mapId}.json`;
    const out = [];
    const p = (message) => out.push({ file, message });
    if (!isObj(data)) { p("oczekiwano obiektu"); return out; }
    if (data.id !== mapId) p(`"id" w pliku ("${data.id}") nie zgadza się z data/maps.json ("${mapId}")`);
    const t = normalizeTeam(team);
    const roleIds = new Set(t.roles.map((r) => r.id));
    const playerIds = new Set(t.players.map((x) => x.id));
    if (!("strategies" in data)) p('brak "strategies"');
    else if (!isObj(data.strategies)) p('"strategies" musi być obiektem');
    else {
      const s = data.strategies;
      checkStrategy(s.pistol, "pistol", roleIds, p);
      checkStrategy(s.backup, "backup", roleIds, p);
      if (s.execute != null && !isObj(s.execute)) p('"strategies.execute" musi być obiektem z kluczami "A" i "B"');
      else if (isObj(s.execute)) VARIANTS.forEach((v) => checkStrategy(s.execute[v], `execute.${v}`, roleIds, p));
    }
    if (data.lineups != null && !Array.isArray(data.lineups)) p('"lineups" musi być listą');
    const seen = new Set();
    arr(data.lineups).forEach((l, i) => {
      if (!isObj(l)) return p(`lineups[${i}] musi być obiektem`);
      const name = isText(l.id) ? l.id : `#${i}`;
      for (const k of LINEUP_REQUIRED) if (!isText(l[k])) p(`lineup "${name}": brak pola "${k}"`);
      if (isText(l.id)) {
        if (seen.has(l.id)) p(`zduplikowane id lineupu "${l.id}"`);
        seen.add(l.id);
      }
      if (isText(l.side) && l.side !== "T" && l.side !== "CT") p(`lineup "${name}": "side" musi być "T" albo "CT"`);
      if (isText(l.player) && !playerIds.has(l.player)) p(`lineup "${name}": nieznany gracz "${l.player}"`);
      if (isText(l.image) && !isRelativePath(l.image)) p(`lineup "${name}": ścieżka "image" ${RELATIVE_HINT}`);
      if (isText(l.resolution) && !RES_RE.test(l.resolution)) {
        p(`lineup "${name}": "resolution" w formacie SZEROKOŚĆxWYSOKOŚĆ, np. 1920x1080`);
      }
    });
    return out;
  }

  // ── roster ──
  function resolveRole(team, roleId) {
    const holders = team.players.filter((p) => p.role === roleId);
    const active = holders.filter((p) => p.status === "active");
    if (active.length) return { kind: "active", players: active };
    const subs = holders.filter((p) => p.status === "sub");
    if (subs.length) return { kind: "sub", players: subs };
    return { kind: "none", players: [] };
  }

  function groupPlayers(team) {
    return {
      active: team.players.filter((p) => p.status !== "sub"),
      subs: team.players.filter((p) => p.status === "sub"),
    };
  }

  function validMe(id, team) {
    return team.players.some((p) => p.id === id) ? id : null;
  }

  function defaultLineupPlayer(team, meId) {
    if (validMe(meId, team)) return meId;
    const { active } = groupPlayers(team);
    if (active.length) return active[0].id;
    return team.players.length ? team.players[0].id : null;
  }

  // ── routing: #<map>/<tab>[/<variant|player>] ──
  function parseHash(hash, { mapIds, playerIds }) {
    const parts = String(hash || "").replace(/^#\/?/, "").split("/").map((x) => {
      try { return decodeURIComponent(x); } catch { return ""; }
    });
    const map = mapIds.includes(parts[0]) ? parts[0] : mapIds[0];
    const tab = TABS.includes(parts[1]) ? parts[1] : TABS[0];
    const v = (parts[2] || "").toUpperCase();
    const variant = tab === "execute" && VARIANTS.includes(v) ? v : "A";
    const player = tab === "lineupy" && playerIds.includes(parts[2]) ? parts[2] : null;
    return { map, tab, variant, player };
  }

  function buildHash({ map, tab, variant, player }) {
    let hash = `#${encodeURIComponent(map)}/${tab}`;
    if (tab === "execute") hash += `/${variant || "A"}`;
    else if (tab === "lineupy" && player) hash += `/${encodeURIComponent(player)}`;
    return hash;
  }

  // ── personal notes ──
  const noteKey = (playerId, mapId, context) => `${NOTE_PREFIX}${playerId}:${mapId}:${context}`;

  function noteContext(tab, variant) {
    if (tab === "pistolowka") return "pistol";
    if (tab === "execute") return `execute-${variant}`;
    if (tab === "notatki") return "map";
    return tab;
  }

  function buildNotesExport(entries, date) {
    const notes = {};
    for (const [k, v] of entries) if (k.startsWith(NOTE_PREFIX) && typeof v === "string") notes[k] = v;
    return { app: "cs2-playbook", version: 1, exportedAt: date.toISOString(), notes };
  }

  function parseNotesImport(text) {
    let data;
    try { data = JSON.parse(String(text).replace(/^﻿/, "")); }
    catch { return { ok: false, error: "Plik nie jest poprawnym JSON-em." }; }
    if (!isObj(data) || data.app !== "cs2-playbook" || data.version !== 1 || !isObj(data.notes)) {
      return { ok: false, error: "To nie jest plik eksportu notatek CS2 Playbook (wersja 1)." };
    }
    const notes = {};
    for (const [k, v] of Object.entries(data.notes)) {
      if (!k.startsWith(NOTE_PREFIX)) return { ok: false, error: `Nieprawidłowy klucz notatki: ${k}` };
      if (typeof v !== "string") return { ok: false, error: `Notatka ${k} nie jest tekstem.` };
      notes[k] = v;
    }
    return { ok: true, notes };
  }

  function exportFilename(date) {
    const pad = (n) => String(n).padStart(2, "0");
    return `cs2-notatki-${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}.json`;
  }

  // ── lineups ──
  function formatResolution(res) {
    if (!isText(res)) return "?";
    return res.replace(/^(\d+)\s*[xX×]\s*(\d+)$/, "$1×$2");
  }

  function lineupFacets(lineups) {
    const uniq = (xs) => [...new Set(xs.filter(isText))];
    const area = (r) => r.split("x").map(Number);
    return {
      sides: uniq(lineups.map((l) => l.side)).sort(),
      resolutions: uniq(lineups.map((l) => l.resolution)).sort((a, b) => {
        const [aw, ah] = area(a), [bw, bh] = area(b);
        return aw - bw || ah - bh || a.localeCompare(b);
      }),
    };
  }

  function filterLineups(lineups, { side, resolution }) {
    return lineups.filter((l) => (side == null || l.side === side) && (resolution == null || l.resolution === resolution));
  }

  return {
    NOTE_PREFIX, ME_KEY, TABS,
    parseJson, plural, normalizeTeam, normalizeMap,
    checkMapsIndex, checkTeam, checkMap,
    resolveRole, groupPlayers, validMe, defaultLineupPlayer,
    parseHash, buildHash,
    noteKey, noteContext, buildNotesExport, parseNotesImport, exportFilename,
    formatResolution, lineupFacets, filterLineups,
  };
})();
</script>
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `node --test tools/test_core.mjs`
Expected: `# pass 19`, `# fail 0`.

- [ ] **Step 6: Commit**

```bash
git add index.html tools/test_core.mjs
git commit -m "Add pure Core module with Node tests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: UI shell (styles, loading, errors, header, tabs, routing, problems bar)

**Files:**
- Modify: `index.html` (add `<style>`, body markup, UI `<script>` after the core script)

**Interfaces:**
- Consumes: `Core.*` from Task 3; data from Task 2.
- Produces (globals in the UI script, used by Tasks 5–7):
  - `h(tag, attrs, ...children) → Element`. `on*` attrs become listeners, `class` sets `className`, `true` → empty attribute, `null`/`false` are skipped. Children may be nested arrays, strings or Nodes.
  - `$(selector) → Element`
  - `store.get/set/remove(key)` and `store.entries(prefix) → [key, value][]`. `set` and `remove` return a boolean and never throw.
  - `app = { maps, team, mapCache, state, problems }`
  - `addProblems(list: {file, message}[])`
  - `currentMe() → string|null`
  - `navigate(partialState)`
  - `route()` (async; re-renders the current view)
  - `VIEWS` (object: tab slug → `(main: Element, { map, state }) => void`)
  - The UI script ends with the line `boot();`. Later tasks insert code **immediately above** that line.

- [ ] **Step 1: Add the stylesheet**

In `index.html`, insert immediately before `</head>`:

```html
<style>
:root {
  --bg: #16181b; --panel: #1c1f23; --border: #2a2d31; --text: #d7dadf; --muted: #8a9099;
  --accent: #6a9f5b; --accent-bg: #22301f; --warn: #d29a3a; --err: #d0544f;
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html, body { margin: 0; background: var(--bg); color: var(--text); font: 13px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
button, select, textarea, input { font: inherit; color: inherit; }
code { font-family: ui-monospace, Menlo, Consolas, monospace; background: var(--panel); padding: 1px 4px; border-radius: 2px; }
header { display: flex; align-items: center; gap: 16px; padding: 8px 16px; border-bottom: 1px solid var(--border); background: var(--panel); }
.brand { font-weight: 700; letter-spacing: .08em; font-size: 12px; color: var(--muted); }
.spacer { flex: 1; }
.seg { display: inline-flex; border: 1px solid var(--border); border-radius: 3px; overflow: hidden; }
.seg button { background: none; border: 0; border-right: 1px solid var(--border); padding: 4px 10px; cursor: pointer; color: var(--muted); }
.seg button:last-child { border-right: 0; }
.seg button:hover { color: var(--text); }
.seg button[aria-pressed="true"] { background: var(--accent-bg); color: var(--accent); }
.me { display: flex; align-items: center; gap: 6px; color: var(--muted); }
select { background: var(--bg); border: 1px solid var(--border); border-radius: 3px; padding: 3px 6px; }
.linkbtn { background: none; border: 0; padding: 0; color: var(--muted); cursor: pointer; text-decoration: underline; }
.linkbtn:hover { color: var(--text); }
nav.tabs { display: flex; gap: 2px; padding: 0 16px; border-bottom: 1px solid var(--border); }
nav.tabs button { background: none; border: 0; border-bottom: 2px solid transparent; padding: 8px 12px; color: var(--muted); cursor: pointer; }
nav.tabs button:hover { color: var(--text); }
nav.tabs button[aria-selected="true"] { color: var(--text); border-bottom-color: var(--accent); }
nav.tabs .sep { width: 1px; background: var(--border); margin: 8px; }
main { padding: 12px 16px 48px; max-width: 1600px; }
h1 { font-size: 16px; margin: 0; }
h2 { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 16px 0 6px; font-weight: 600; }
.titlebar { display: flex; align-items: center; gap: 10px; margin: 8px 0 12px; }
.badge { font-size: 10px; font-weight: 700; letter-spacing: .06em; border: 1px solid var(--warn); color: var(--warn); padding: 1px 5px; border-radius: 2px; }
.split { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 16px; align-items: start; }
.shot { display: block; max-width: 100%; max-height: 70vh; object-fit: contain; background: #0f1012; border: 1px solid var(--border); cursor: zoom-in; }
.missing { display: flex; align-items: center; justify-content: center; min-height: 120px; padding: 12px; border: 1px solid var(--err); color: var(--err); background: #1a1315; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12px; word-break: break-all; }
.pre { white-space: pre-wrap; margin: 0; }
ol.steps { margin: 0; padding-left: 20px; }
ol.steps li { margin: 2px 0; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; vertical-align: top; padding: 5px 8px; border-bottom: 1px solid var(--border); }
th { font-size: 11px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.muted { color: var(--muted); }
.warn { color: var(--warn); }
.err { color: var(--err); }
.empty { padding: 24px; border: 1px dashed var(--border); color: var(--muted); text-align: center; }
.notes { margin-top: 8px; }
.notes textarea { width: 100%; min-height: 70px; resize: vertical; background: var(--bg); border: 1px solid var(--border); border-radius: 3px; padding: 6px; }
.notes textarea:focus { outline: 1px solid var(--accent); }
.notes textarea:disabled { opacity: .5; }
.notes .bar { display: flex; align-items: center; gap: 10px; margin-top: 4px; font-size: 12px; }
.layout-lineups { display: grid; grid-template-columns: 200px minmax(0, 1fr); gap: 16px; }
.plist button { display: flex; justify-content: space-between; width: 100%; background: none; border: 0; border-left: 2px solid transparent; padding: 4px 8px; color: var(--muted); cursor: pointer; text-align: left; }
.plist button:hover { color: var(--text); }
.plist button[aria-pressed="true"] { color: var(--text); border-left-color: var(--accent); background: var(--accent-bg); }
.filters { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; margin-bottom: 4px; }
.filters > span { display: flex; align-items: center; gap: 6px; }
.lineup { display: grid; grid-template-columns: minmax(0, 360px) minmax(0, 1fr); gap: 16px; padding: 12px 0; border-bottom: 1px solid var(--border); }
.lineup .shot { max-height: 220px; }
.res { font-family: ui-monospace, Menlo, Consolas, monospace; color: var(--accent); border: 1px solid var(--accent); padding: 0 5px; border-radius: 2px; }
.kv { display: grid; grid-template-columns: auto 1fr; gap: 2px 12px; margin: 0; }
.kv dt { color: var(--muted); }
.kv dd { margin: 0; }
.fatal { max-width: 720px; margin: 48px auto; padding: 16px; border: 1px solid var(--err); }
.fatal h1 { color: var(--err); margin-bottom: 8px; }
#problems { position: fixed; left: 0; right: 0; bottom: 0; background: #231c12; border-top: 1px solid var(--warn); color: var(--warn); font-size: 12px; max-height: 40vh; overflow: auto; }
#problems summary { padding: 6px 16px; cursor: pointer; }
#problems ul { margin: 0; padding: 0 16px 8px 32px; }
#lightbox { position: fixed; inset: 0; z-index: 10; background: rgba(0, 0, 0, .92); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 16px; cursor: zoom-out; }
#lightbox img { max-width: 100%; max-height: calc(100vh - 64px); object-fit: contain; }
#lightbox .cap { margin-top: 8px; color: var(--muted); font-size: 12px; }
#lightbox button { position: absolute; top: 10px; right: 14px; background: none; border: 1px solid var(--border); color: var(--text); padding: 2px 8px; cursor: pointer; }
@media (max-width: 1000px) {
  header { flex-wrap: wrap; }
  .split, .lineup, .layout-lineups { grid-template-columns: 1fr; }
}
</style>
```

- [ ] **Step 2: Add the body markup**

Insert immediately after `<body>`:

```html
<header id="top" hidden>
  <span class="brand">CS2 PLAYBOOK</span>
  <div class="seg" id="maps" role="group" aria-label="Mapa"></div>
  <span class="spacer"></span>
  <label class="me">Kim jestem: <select id="me"></select></label>
</header>
<nav class="tabs" id="tabs" role="tablist" hidden></nav>
<main id="main"><p class="muted">Wczytywanie…</p></main>
<details id="problems" hidden><summary></summary><ul></ul></details>
<div id="lightbox" hidden><button type="button" aria-label="Zamknij">✕</button><img alt=""><div class="cap"></div></div>
```

- [ ] **Step 3: Add the UI script**

Insert immediately before `</body>` (after the core script):

```html
<script>
"use strict";
const $ = (sel) => document.querySelector(sel);

function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat(Infinity)) {
    if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
  }
  return el;
}

// localStorage that never throws (private mode, blocked storage, quota)
const store = {
  get(key) { try { return localStorage.getItem(key); } catch { return null; } },
  set(key, value) { try { localStorage.setItem(key, value); return true; } catch { return false; } },
  remove(key) { try { localStorage.removeItem(key); return true; } catch { return false; } },
  entries(prefix) {
    const out = [];
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.startsWith(prefix)) out.push([k, localStorage.getItem(k)]);
      }
    } catch { /* storage unavailable: nothing to list */ }
    return out;
  },
};

const app = { maps: [], team: { roles: [], players: [] }, mapCache: new Map(), state: null, problems: new Map() };

const TAB_LABELS = { pistolowka: "Pistolówka", execute: "Execute", backup: "Backup", lineupy: "Lineupy", notatki: "Notatki" };

async function loadJson(path) {
  let res;
  try {
    res = await fetch(path, { cache: "no-cache" });
  } catch (err) {
    console.error(`[playbook] fetch ${path}`, err);
    throw new Error(`${path}: nie udało się pobrać pliku (błąd sieci)`);
  }
  if (!res.ok) throw new Error(`${path}: nie udało się pobrać pliku (HTTP ${res.status})`);
  return Core.parseJson(await res.text(), path);
}

function addProblems(list) {
  for (const p of list) {
    const key = `${p.file}: ${p.message}`;
    if (app.problems.has(key)) continue;
    app.problems.set(key, p);
    console.warn(`[playbook] ${key}`);
  }
  const box = $("#problems");
  const n = app.problems.size;
  box.hidden = n === 0;
  box.querySelector("summary").textContent = `⚠ ${n} ${Core.plural(n, "problem", "problemy", "problemów")} w danych`;
  box.querySelector("ul").replaceChildren(...[...app.problems.keys()].map((k) => h("li", null, k)));
}

function showFatal(title, message) {
  $("#top").hidden = true;
  $("#tabs").hidden = true;
  $("#main").replaceChildren(h("div", { class: "fatal" }, h("h1", null, title), h("p", { class: "pre" }, message)));
}

function currentMe() {
  const id = store.get(Core.ME_KEY);
  const valid = Core.validMe(id, app.team);
  if (id && !valid) store.remove(Core.ME_KEY);
  return valid;
}

function renderMePicker() {
  const sel = $("#me");
  const { active, subs } = Core.groupPlayers(app.team);
  const opt = (p) => h("option", { value: p.id }, p.name || p.id);
  sel.replaceChildren(
    h("option", { value: "" }, "— wybierz —"),
    active.map(opt),
    subs.length ? h("optgroup", { label: "Rezerwowi" }, subs.map(opt)) : null,
  );
  sel.value = currentMe() || "";
  sel.addEventListener("change", () => {
    if (sel.value) store.set(Core.ME_KEY, sel.value);
    else store.remove(Core.ME_KEY);
    route();
  });
}

function renderMapButtons() {
  $("#maps").replaceChildren(...app.maps.map((m) => h("button", {
    type: "button",
    "aria-pressed": String(m.id === app.state.map),
    onclick: () => navigate({ map: m.id, player: null }),
  }, m.name || m.id)));
}

function renderTabs() {
  const tab = (t) => h("button", {
    type: "button", role: "tab",
    "aria-selected": String(app.state.tab === t),
    onclick: () => navigate({ tab: t }),
  }, TAB_LABELS[t]);
  $("#tabs").replaceChildren(tab("pistolowka"), tab("execute"), tab("backup"), h("span", { class: "sep" }), tab("lineupy"), tab("notatki"));
}

function navigate(partial) {
  location.hash = Core.buildHash({ ...app.state, ...partial });
}

function getMap(id) {
  if (!app.mapCache.has(id)) {
    const promise = loadJson(`data/${id}.json`).then((data) => {
      addProblems(Core.checkMap(data, id, app.team));
      return Core.normalizeMap(data);
    });
    promise.catch(() => app.mapCache.delete(id)); // retry on next navigation
    app.mapCache.set(id, promise);
  }
  return app.mapCache.get(id);
}

async function route() {
  const s = Core.parseHash(location.hash, {
    mapIds: app.maps.map((m) => m.id),
    playerIds: app.team.players.map((p) => p.id),
  });
  const canonical = Core.buildHash(s);
  if (location.hash !== canonical) history.replaceState(null, "", canonical);
  app.state = s;
  renderMapButtons();
  renderTabs();
  const mapName = (app.maps.find((m) => m.id === s.map) || {}).name || s.map;
  document.title = `${mapName} · ${TAB_LABELS[s.tab]} — CS2 Playbook`;
  const main = $("#main");
  let map;
  try {
    map = await getMap(s.map);
  } catch (err) {
    console.error("[playbook]", err);
    if (app.state === s) {
      main.replaceChildren(h("div", { class: "fatal" }, h("h1", null, "Nie udało się wczytać mapy"), h("p", { class: "pre" }, err.message)));
    }
    return;
  }
  if (app.state !== s) return; // a newer navigation started while loading
  main.replaceChildren();
  const view = VIEWS[s.tab];
  if (view) view(main, { map, state: s });
}

async function boot() {
  if (location.protocol === "file:") {
    showFatal("Uruchom przez lokalny serwer",
      "Przeglądarka blokuje wczytywanie plików JSON z file://.\n\nW folderze repozytorium uruchom:\n\n    python3 -m http.server 8000\n\ni otwórz http://localhost:8000");
    return;
  }
  try {
    const [mapsIdx, team] = await Promise.all([loadJson("data/maps.json"), loadJson("data/team.json")]);
    app.maps = (Array.isArray(mapsIdx && mapsIdx.maps) ? mapsIdx.maps : [])
      .filter((m) => m && typeof m.id === "string" && /^[a-z0-9-]+$/.test(m.id));
    app.team = Core.normalizeTeam(team);
    addProblems([...Core.checkMapsIndex(mapsIdx), ...Core.checkTeam(team)]);
  } catch (err) {
    console.error("[playbook]", err);
    showFatal("Nie udało się wczytać danych", err.message);
    return;
  }
  if (!app.maps.length) {
    showFatal("Brak map", "Plik data/maps.json nie zawiera żadnej poprawnej mapy.");
    return;
  }
  $("#top").hidden = false;
  $("#tabs").hidden = false;
  renderMePicker();
  window.addEventListener("hashchange", route);
  await route();
}

// ── views: each later section registers VIEWS[<tab>] ──
const VIEWS = {};

boot();
</script>
```

- [ ] **Step 4: Re-run the Core tests (regression)**

Run: `node --test tools/test_core.mjs`
Expected: `# fail 0`. The regex still finds `<script id="core">`, and the UI script is a separate block.

- [ ] **Step 5: Verify in the browser**

Start: `python3 -m http.server 8000 --directory "$(dirname "$PWD")"` and open `http://localhost:8000/TacticsCS2/`.

Expected:
- The header shows `CS2 PLAYBOOK`, a highlighted `Mirage` button, and "Kim jestem" with "— wybierz —", 5 players and a "Rezerwowi" group containing `PRZYKŁAD Rezerwa 1`.
- The tabs show Pistolówka (selected), Execute, Backup | Lineupy, Notatki.
- The URL becomes `…/TacticsCS2/#mirage/pistolowka`.
- Clicking Execute changes the URL to `#mirage/execute/A`. Pressing Back returns to `#mirage/pistolowka`.
- `#mirage/execute/b` canonicalises to `#mirage/execute/B`.
- No problems bar. The console has no errors.

Error checks (undo each one afterwards):
- Add a trailing comma after the last player in `data/team.json` and reload. Expected: a full-page "Nie udało się wczytać danych" with `data/team.json: błąd składni JSON — linia N, kolumna M`, where N:M is the `]` right after the comma. Revert.
- In `data/maps.json`, add `{ "id": "dust2", "name": "Dust II" }`, reload, and click Dust II. Expected: the content area shows "Nie udało się wczytać mapy" with `data/dust2.json: nie udało się pobrać pliku (HTTP 404)`, and the Mirage button still works. Revert.
- In `data/team.json`, change `p2`'s role to `"entry"` and reload. Expected: the bottom bar shows `⚠ 1 problem w danych`, and expanding it shows `data/team.json: rola "entry" ma kilku aktywnych graczy: p1, p2`. Revert.
- Open `index.html` directly (`open index.html`). Expected: "Uruchom przez lokalny serwer" with the command.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "Add UI shell: loading, errors, header, tabs, hash routing

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Personal notes (widget, Notatki tab, export/import)

**Files:**
- Modify: `index.html` (header markup, UI script above `boot();`)

**Interfaces:**
- Consumes: `h`, `$`, `store`, `app`, `currentMe`, `route`, `VIEWS`, `Core.noteKey`, `Core.NOTE_PREFIX`, `Core.buildNotesExport`, `Core.parseNotesImport`, `Core.exportFilename`, `Core.plural`.
- Produces:
  - `notesWidget(mapId: string, context: string, label = "Moje notatki") → Element`. This is the self-contained autosaving textarea. Tasks 6 and 7 use it.
  - `flushNoteSaves()`
  - `VIEWS.notatki`

- [ ] **Step 1: Add the export/import controls to the header**

In `index.html`, replace:

```html
  <label class="me">Kim jestem: <select id="me"></select></label>
</header>
```

with:

```html
  <label class="me">Kim jestem: <select id="me"></select></label>
  <button type="button" class="linkbtn" id="export-notes">Eksport notatek</button>
  <button type="button" class="linkbtn" id="import-notes">Import notatek</button>
  <input type="file" id="import-file" accept="application/json,.json" hidden>
  <span id="io-status" class="muted" role="status"></span>
</header>
```

- [ ] **Step 2: Flush pending saves before every re-render**

In the UI script, replace the first line of `route()`'s body:

```js
async function route() {
  const s = Core.parseHash(location.hash, {
```

with:

```js
async function route() {
  flushNoteSaves();
  const s = Core.parseHash(location.hash, {
```

- [ ] **Step 3: Add the notes code**

Insert immediately above the final `boot();` line:

```js
// ── personal notes ──
const pendingNoteSaves = new Set();
function flushNoteSaves() {
  for (const save of [...pendingNoteSaves]) save();
}
window.addEventListener("pagehide", flushNoteSaves);

function notesWidget(mapId, context, label = "Moje notatki") {
  const me = currentMe();
  const wrap = h("div", { class: "notes" }, h("h2", null, label));
  const ta = h("textarea", {
    "aria-label": label,
    disabled: !me,
    placeholder: me ? "Twoje prywatne notatki — zapisują się automatycznie w tej przeglądarce." : "Wybierz gracza w „Kim jestem”, aby pisać notatki.",
  });
  wrap.append(ta);
  if (!me) return wrap;

  const key = Core.noteKey(me, mapId, context);
  ta.value = store.get(key) || "";
  const status = h("span", { class: "muted" });
  let timer = null;
  const save = () => {
    clearTimeout(timer);
    timer = null;
    pendingNoteSaves.delete(save);
    const ok = ta.value.trim() ? store.set(key, ta.value) : store.remove(key);
    status.className = ok ? "muted" : "err";
    status.textContent = ok ? "✓ zapisano" : "✗ nie zapisano — pamięć przeglądarki niedostępna";
  };
  ta.addEventListener("input", () => {
    status.textContent = "";
    clearTimeout(timer);
    timer = setTimeout(save, 400);
    pendingNoteSaves.add(save);
  });
  ta.addEventListener("blur", () => { if (timer) save(); });

  const clearBtn = h("button", { type: "button", class: "linkbtn" }, "Wyczyść");
  const confirmBox = h("span", { hidden: true }, "Na pewno? ",
    h("button", { type: "button", class: "linkbtn", onclick: () => { ta.value = ""; save(); confirmBox.hidden = true; clearBtn.hidden = false; } }, "Tak"),
    " ",
    h("button", { type: "button", class: "linkbtn", onclick: () => { confirmBox.hidden = true; clearBtn.hidden = false; } }, "Nie"));
  clearBtn.addEventListener("click", () => { clearBtn.hidden = true; confirmBox.hidden = false; });
  wrap.append(h("div", { class: "bar" }, status, h("span", { class: "spacer" }), clearBtn, confirmBox));
  return wrap;
}

VIEWS.notatki = (main, { state }) => {
  const mapName = (app.maps.find((m) => m.id === state.map) || {}).name || state.map;
  main.append(
    h("div", { class: "titlebar" }, h("h1", null, `Notatki — ${mapName}`)),
    h("p", { class: "muted" }, "Prywatne notatki do całej mapy. Zapisują się tylko w tej przeglądarce na tym urządzeniu — użyj eksportu, aby je przenieść."),
    notesWidget(state.map, "map", "Moje notatki do mapy"),
  );
};

function ioStatus(message, isError) {
  const el = $("#io-status");
  el.className = isError ? "err" : "muted";
  el.textContent = message;
}

function exportNotes() {
  flushNoteSaves();
  const now = new Date();
  const data = Core.buildNotesExport(store.entries(Core.NOTE_PREFIX), now);
  const n = Object.keys(data.notes).length;
  if (!n) return ioStatus("Brak notatek do eksportu.");
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = h("a", { href: url, download: Core.exportFilename(now) });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  ioStatus(`Wyeksportowano ${n} ${Core.plural(n, "notatkę", "notatki", "notatek")}.`);
}

async function importNotes(file) {
  let text;
  try { text = await file.text(); } catch { return ioStatus("Nie udało się odczytać pliku.", true); }
  const result = Core.parseNotesImport(text);
  if (!result.ok) return ioStatus(result.error, true);
  let saved = 0, failed = 0;
  for (const [k, v] of Object.entries(result.notes)) {
    if (!v.trim()) continue;
    if (store.set(k, v)) saved++; else failed++;
  }
  if (failed) ioStatus(`Zaimportowano ${saved}, nie zapisano ${failed} — pamięć przeglądarki niedostępna.`, true);
  else ioStatus(`Zaimportowano ${saved} ${Core.plural(saved, "notatkę", "notatki", "notatek")}.`);
  route();
}

$("#export-notes").addEventListener("click", exportNotes);
$("#import-notes").addEventListener("click", () => $("#import-file").click());
$("#import-file").addEventListener("change", (e) => {
  const file = e.target.files[0];
  e.target.value = ""; // allow importing the same file again
  if (file) importNotes(file);
});

```

- [ ] **Step 4: Re-run the Core tests (regression)**

Run: `node --test tools/test_core.mjs`
Expected: `# fail 0`.

- [ ] **Step 5: Verify in the browser** (`http://localhost:8000/TacticsCS2/#mirage/notatki`)

1. With "— wybierz —", the textarea is disabled and shows the "Wybierz gracza…" placeholder.
2. Pick `PRZYKŁAD Gracz 1` and type `abc`. Expected: `✓ zapisano` appears after about 0.4 s. Reload: `abc` is still there.
3. Switch to `PRZYKŁAD Rezerwa 1`. Expected: an empty textarea. Type `sub`, switch back to Gracz 1, and `abc` is shown.
4. Click Wyczyść → "Na pewno? Tak / Nie" → Nie: the text stays. Click Wyczyść → Tak: the textarea is empty. Reload: still empty. DevTools → Application → Local Storage shows no `…:p1:mirage:map` key.
5. **Flush check (Review Focus 3):** type `fast` and click the `Pistolówka` tab immediately (within 400 ms), then click `Notatki`. Expected: `fast` is still there. Then type `fast2` and press ⌘R right away. Expected: after the reload, `fast2` is there.
6. Click "Eksport notatek". Expected: `cs2-notatki-<today>.json` downloads and contains `"app": "cs2-playbook"` and the `s1` note. The status reads "Wyeksportowano 2 notatki." (or the count matching your notes).
7. Clear the notes in Local Storage (DevTools), import the exported file, and confirm "Zaimportowano N …" and that the text is back. Import any non-export JSON (e.g. `data/team.json`). Expected: a red message "To nie jest plik eksportu notatek CS2 Playbook (wersja 1)."
8. Set `cs2pb:v1:me` to `ghost` in Local Storage and reload. Expected: the picker shows "— wybierz —" and nothing crashes (Review Focus 4).

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "Add personal notes with autosave, map notes tab, export/import

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Strategy tabs (Pistolówka, Execute A/B, Backup), images, lightbox

**Files:**
- Modify: `index.html` (UI script above `boot();`)

**Interfaces:**
- Consumes: `h`, `$`, `app`, `addProblems`, `navigate`, `VIEWS`, `notesWidget`, `Core.resolveRole`, `Core.noteContext`, `Core.formatResolution`.
- Produces:
  - `shot(path, caption, sourceFile) → Element|null`. It is an image with a missing-file placeholder and opens the lightbox on click. Task 7 uses it.
  - `openLightbox(path, caption)`
  - `VIEWS.pistolowka`, `VIEWS.execute`, `VIEWS.backup`

- [ ] **Step 1: Add the code**

Insert immediately above the final `boot();` line:

```js
// ── images + lightbox ──
function shot(path, caption, sourceFile) {
  if (!path) return null;
  const img = h("img", { class: "shot", src: path, alt: caption || path, loading: "lazy" });
  img.addEventListener("error", () => {
    addProblems([{ file: sourceFile, message: `brak pliku obrazka "${path}"` }]);
    img.replaceWith(h("div", { class: "missing" }, `Brak pliku: ${path}`));
  }, { once: true });
  img.addEventListener("click", () => openLightbox(path, caption));
  return img;
}

function openLightbox(path, caption) {
  const lb = $("#lightbox");
  lb.querySelector("img").src = path;
  lb.querySelector(".cap").textContent = caption ? `${caption} · ${path}` : path;
  lb.hidden = false;
  lb.querySelector("button").focus();
}

function closeLightbox() {
  const lb = $("#lightbox");
  lb.hidden = true;
  lb.querySelector("img").removeAttribute("src");
}

$("#lightbox").addEventListener("click", closeLightbox);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#lightbox").hidden) closeLightbox();
});

// ── strategy tabs ──
function playerCell(roleId) {
  const res = Core.resolveRole(app.team, roleId);
  if (res.kind === "none") return h("span", { class: "warn" }, "— brak gracza");
  const names = res.players.map((p) => p.name || p.id).join(", ");
  return res.kind === "sub" ? [names, " ", h("span", { class: "muted" }, "(rezerwa)")] : names;
}

function assignmentsTable(rows) {
  const roleName = (id) => (app.team.roles.find((r) => r.id === id) || {}).name;
  return h("table", null,
    h("thead", null, h("tr", null, ["Rola", "Gracz", "Pozycja", "Utility", "Zadanie", "Timing", "Uwagi"].map((t) => h("th", null, t)))),
    h("tbody", null, rows.map((r) => h("tr", null,
      h("td", null, roleName(r.role) || h("span", { class: "warn" }, `⚠ nieznana rola: ${r.role ?? "(brak)"}`)),
      h("td", null, playerCell(r.role)),
      ["position", "utility", "action", "timing", "notes"].map((k) => h("td", { class: "pre" }, r[k] ?? "")),
    ))));
}

function renderStrategyTab(main, { map, state }) {
  const file = `data/${state.map}.json`;
  const slot = { pistolowka: "pistol", execute: "execute", backup: "backup" }[state.tab];
  if (slot === "execute") {
    main.append(h("div", { class: "titlebar" },
      h("span", { class: "muted" }, "Bombsite:"),
      h("div", { class: "seg", role: "group", "aria-label": "Bombsite" }, ["A", "B"].map((v) => h("button", {
        type: "button",
        "aria-pressed": String(state.variant === v),
        onclick: () => navigate({ variant: v }),
      }, v)))));
  }
  const strat = slot === "execute" ? map.strategies.execute[state.variant] : map.strategies[slot];
  const context = Core.noteContext(state.tab, state.variant);

  if (!strat) {
    main.append(h("div", { class: "empty" },
      slot === "execute" ? `Brak strategii dla bombsite ${state.variant}.` : "Brak strategii.",
      h("br"),
      h("span", { class: "muted" }, `Dodaj ją w ${file}.`)));
    main.append(notesWidget(state.map, context));
    return;
  }

  main.append(h("div", { class: "titlebar" },
    h("h1", null, strat.title || "(bez tytułu)"),
    strat.example ? h("span", { class: "badge", title: "Przykładowe dane — podmień na własną strategię" }, "PRZYKŁAD") : null));

  const text = h("div", null,
    strat.summary ? [h("h2", null, "Opis"), h("p", { class: "pre" }, strat.summary)] : null,
    strat.steps.length ? [h("h2", null, "Kroki"), h("ol", { class: "steps" }, strat.steps.map((s) => h("li", null, s)))] : null);
  main.append(strat.image ? h("div", { class: "split" }, h("div", null, shot(strat.image, strat.title, file)), text) : text);

  if (strat.assignments.length) main.append(h("h2", null, "Zadania graczy"), assignmentsTable(strat.assignments));
  if (strat.notes) main.append(h("h2", null, "Notatki zespołu"), h("p", { class: "pre" }, strat.notes));
  main.append(notesWidget(state.map, context));
}

VIEWS.pistolowka = renderStrategyTab;
VIEWS.execute = renderStrategyTab;
VIEWS.backup = renderStrategyTab;

```

- [ ] **Step 2: Re-run the Core tests (regression)**

Run: `node --test tools/test_core.mjs`
Expected: `# fail 0`.

- [ ] **Step 3: Verify in the browser** (`http://localhost:8000/TacticsCS2/`)

1. **Pistolówka:** the title has a PRZYKŁAD badge, the SVG is on the left and fully visible, and Opis and 3 Kroki are on the right. The table has 5 rows, with "Gracz" filled from `team.json` (`PRZYKŁAD Gracz 1` for Entry). Notatki zespołu and Moje notatki come after it.
2. **Execute:** the `Bombsite: [A|B]` toggle shows with A active, and A has 4 steps. Click B: the URL changes to `#mirage/execute/B`, you see "Brak strategii dla bombsite B. Dodaj ją w data/mirage.json.", and the notes field is still there. A note typed under B does not appear under A.
3. **Backup:** shows the image, Opis and a 2-row table, with no "Kroki" heading (steps are empty).
4. **Lightbox:** click any image. It opens full-screen with the caption `<title> · assets/…svg`. Esc closes it. Clicking anywhere also closes it.
5. **Missing image:** temporarily change the pistol `image` to `assets/tactics/mirage/nope.png` and reload. Expected: a red box reading `Brak pliku: assets/tactics/mirage/nope.png`, and the problems bar shows `data/mirage.json: brak pliku obrazka "assets/tactics/mirage/nope.png"`. Revert.
6. **Sub takes over:** in `team.json`, set `s1.role` to `"lurk"` and `p4.role` to `null`, then reload Pistolówka. Expected: the Lurk row reads `PRZYKŁAD Rezerwa 1 (rezerwa)`. Then set `s1.role` back to `null` and reload. Expected: Lurk reads `— brak gracza` in orange. Revert both.
7. No console errors on clean data.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "Add strategy tabs with A/B execute toggle, role tables and lightbox

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Lineupy tab

**Files:**
- Modify: `index.html` (UI script above `boot();`)

**Interfaces:**
- Consumes: `h`, `app`, `navigate`, `currentMe`, `VIEWS`, `notesWidget`, `shot`, `Core.groupPlayers`, `Core.defaultLineupPlayer`, `Core.lineupFacets`, `Core.filterLineups`, `Core.formatResolution`.
- Produces: `VIEWS.lineupy`.

- [ ] **Step 1: Add the code**

Insert immediately above the final `boot();` line:

```js
// ── lineups tab ──
function lineupRow(l, mapId, file) {
  const res = `${Core.formatResolution(l.resolution)}${l.aspect ? ` · ${l.aspect}` : ""}`;
  const kv = (k, v) => (v ? [h("dt", null, k), h("dd", null, v)] : null);
  return h("div", { class: "lineup" },
    h("div", null, shot(l.image, `${l.name} · ${res}`, file)),
    h("div", null,
      h("div", { class: "titlebar" },
        h("h1", null, l.name || l.id),
        h("span", { class: "res", title: "Rozdzielczość / proporcje, dla których działa ten lineup" }, res),
        l.example ? h("span", { class: "badge" }, "PRZYKŁAD") : null),
      h("dl", { class: "kv" }, kv("Cel", l.target), kv("Strona", l.side), kv("Skąd", l.from), kv("Rzut", l.throw)),
      l.instructions ? [h("h2", null, "Instrukcja"), h("p", { class: "pre" }, l.instructions)] : null,
      l.notes ? [h("h2", null, "Notatki zespołu"), h("p", { class: "pre" }, l.notes)] : null,
      notesWidget(mapId, `lineup:${l.id}`)));
}

VIEWS.lineupy = (main, { map, state }) => {
  const file = `data/${state.map}.json`;
  const mapName = (app.maps.find((m) => m.id === state.map) || {}).name || state.map;
  const playerId = state.player || Core.defaultLineupPlayer(app.team, currentMe());
  const { active, subs } = Core.groupPlayers(app.team);
  const count = (id) => map.lineups.filter((l) => l.player === id).length;
  const playerBtn = (p) => h("button", {
    type: "button",
    "aria-pressed": String(p.id === playerId),
    onclick: () => navigate({ player: p.id }),
  }, h("span", null, p.name || p.id), h("span", { class: "muted" }, String(count(p.id))));

  const content = h("div");
  main.append(h("div", { class: "layout-lineups" },
    h("div", { class: "plist" },
      h("h2", null, "Skład"), active.map(playerBtn),
      subs.length ? [h("h2", null, "Rezerwowi"), subs.map(playerBtn)] : null),
    content));

  const player = app.team.players.find((p) => p.id === playerId);
  if (!player) {
    content.append(h("div", { class: "empty" }, "Brak graczy w data/team.json."));
    return;
  }
  const mine = map.lineups.filter((l) => l.player === playerId);
  if (!mine.length) {
    content.append(h("div", { class: "empty" }, `Brak lineupów dla ${player.name || player.id} na ${mapName}.`, h("br"),
      h("span", { class: "muted" }, `Dodaj je w ${file} i assets/lineups/${state.map}/${player.id}/.`)));
    return;
  }

  const filter = { side: null, resolution: null };
  const list = h("div");
  const draw = () => list.replaceChildren(...Core.filterLineups(mine, filter).map((l) => lineupRow(l, state.map, file)));
  const chips = (label, key, values, fmt) => {
    if (values.length < 2) return null;
    const seg = h("div", { class: "seg", role: "group", "aria-label": label });
    for (const v of [null, ...values]) {
      seg.append(h("button", {
        type: "button",
        "aria-pressed": String(filter[key] === v),
        onclick: (e) => {
          filter[key] = v;
          for (const b of seg.children) b.setAttribute("aria-pressed", String(b === e.currentTarget));
          draw();
        },
      }, v === null ? "Wszystkie" : fmt(v)));
    }
    return h("span", null, h("span", { class: "muted" }, label), seg);
  };
  const facets = Core.lineupFacets(mine);
  content.append(
    h("div", { class: "filters" },
      chips("Strona:", "side", facets.sides, (v) => v),
      chips("Rozdzielczość:", "resolution", facets.resolutions, Core.formatResolution)),
    list);
  draw();
};

```

- [ ] **Step 2: Re-run the Core tests (regression)**

Run: `node --test tools/test_core.mjs`
Expected: `# fail 0`.

- [ ] **Step 3: Verify in the browser** (`http://localhost:8000/TacticsCS2/#mirage/lineupy`)

1. With no "Kim jestem" set, `PRZYKŁAD Gracz 1` is selected. The left list shows "Skład" (5 players, with counts 2, 1, 0, 0, 0) and "Rezerwowi" (`PRZYKŁAD Rezerwa 1`, 0).
2. Gracz 1 shows 2 rows, each with a thumbnail (no cropping: the 2560×1440 SVG's dashed border is fully visible), a `1920×1080 · 16:9` or `2560×1440 · 16:9` label, Cel/Strona/Skąd/Rzut and Moje notatki.
3. The "Rozdzielczość:" chips (Wszystkie / 1920×1080 / 2560×1440) filter the list. There are no "Strona:" chips, because both lineups are T.
4. Click Gracz 2: the URL changes to `#mirage/lineupy/p2` and there is one lineup labelled `1280×960 · 4:3`. Click Gracz 3: "Brak lineupów dla PRZYKŁAD Gracz 3 na Mirage."
5. Set "Kim jestem" to Gracz 2 and open `#mirage/lineupy`. Expected: Gracz 2 is preselected.
6. Click a thumbnail: the lightbox shows the full image with its resolution in the caption.
7. A note typed on `example-smoke-1` does not appear on `example-smoke-2`.
8. Narrow the window below 1000 px. Expected: the columns stack and there is no horizontal page scroll.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "Add lineups tab with player list, resolution/side filters

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Polish README and full end-to-end verification

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: user documentation.

- [ ] **Step 1: Write `README.md`**

````markdown
# CS2 Playbook

Prywatna ściąga taktyczna naszej drużyny CS2: trzy strategie na mapę (pistolówka, execute A/B, backup), zadania graczy oraz osobiste lineupy smoke'ów.

Strona jest w pełni statyczna: jeden plik `index.html` + dane w `data/*.json` + obrazki w `assets/`. Nie ma backendu, bazy danych ani kont.

> **Uwaga o prywatności:** strona na GitHub Pages jest publicznie dostępna pod swoim adresem (nawet gdy repozytorium jest prywatne). Strona ma `noindex`, więc nie trafi do wyszukiwarek, ale każdy, kto zna link, może ją otworzyć. Nie wrzucaj tu niczego, czego nie chcesz pokazać.

## Uruchomienie lokalne

Otwarcie `index.html` podwójnym kliknięciem **nie zadziała** (przeglądarka blokuje wczytywanie JSON z `file://`). W folderze repozytorium uruchom:

```bash
python3 -m http.server 8000
```

i otwórz <http://localhost:8000>.

## Publikacja (GitHub Pages)

1. Wypchnij repozytorium na GitHub.
2. **Settings → Pages → Build and deployment → Deploy from a branch**, gałąź `main`, folder `/ (root)`.
3. Po minucie strona będzie pod `https://<użytkownik>.github.io/<repozytorium>/`.

Każdy kolejny `git push` aktualizuje stronę (zwykle w ciągu 1–2 minut). Wszystkie ścieżki są względne, więc działa to też z podkatalogu repozytorium.

## Struktura

```
index.html                  aplikacja (nie trzeba jej edytować przy dodawaniu treści)
data/maps.json              lista map i ich kolejność
data/team.json              role i gracze (skład + rezerwowi)
data/<mapa>.json            strategie i lineupy dla mapy
assets/tactics/<mapa>/      screenshoty / diagramy strategii
assets/lineups/<mapa>/<id-gracza>/   screenshoty lineupów
tools/validate.py           sprawdzanie danych przed pushem
```

## Przed każdym pushem

```bash
python3 tools/validate.py
```

Sprawdza składnię JSON, odwołania do ról i graczy, unikalność id, czy każdy obrazek istnieje **i czy wielkość liter w nazwie pliku się zgadza**. macOS i Windows ignorują wielkość liter, GitHub Pages nie — `Window.png` ≠ `window.png`. Najprościej: nazwy plików zawsze małymi literami.

Problemy w danych widać też na stronie — pasek „⚠ N problemów w danych” na dole ekranu.

## Dodanie lineupu (najczęstsza czynność)

1. Zrób screenshot w grze. Zapisz go jako np.
   `assets/lineups/mirage/p1/window-t-spawn-1920x1080.png`
   (folder = id mapy / id gracza; w nazwie pliku rozdzielczość).
2. Dopisz wpis do `"lineups"` w `data/mirage.json`:

   ```json
   {
     "id": "window-t-spawn",
     "player": "p1",
     "name": "Window",
     "target": "Mid window",
     "side": "T",
     "from": "T spawn",
     "throw": "jumpthrow",
     "resolution": "1920x1080",
     "aspect": "16:9",
     "image": "assets/lineups/mirage/p1/window-t-spawn-1920x1080.png",
     "instructions": "Stań w rogu przy ...",
     "notes": ""
   }
   ```

   Wymagane: `id`, `player`, `name`, `target`, `side` (`T` albo `CT`), `resolution` (np. `1920x1080`), `image`. Reszta jest opcjonalna.
   `id` musi być unikalne w obrębie mapy — przypisane są do niego prywatne notatki, więc lepiej go potem nie zmieniać.
3. `python3 tools/validate.py`, potem `git add`, `git commit`, `git push`.

Samo skopiowanie obrazka do folderu **nie** wystarczy — strona statyczna nie widzi zawartości folderów, dlatego każdy obrazek musi mieć wpis w JSON.

Ten sam smoke na inną rozdzielczość = osobny wpis z innym `id`, `resolution` i plikiem.

## Strategie (pistolówka, execute A/B, backup)

Każda mapa ma dokładnie trzy sloty w `"strategies"`: `pistol`, `execute` (z wariantami `A` i `B`) oraz `backup`. Każda strategia ma ten sam format:

```json
{
  "title": "Nazwa strategii",
  "summary": "Opis. Nowa linia: \n",
  "image": "assets/tactics/mirage/execute-a.png",
  "steps": ["Krok 1", "Krok 2"],
  "assignments": [
    { "role": "entry", "position": "Palace", "utility": "2× flash", "action": "pierwszy na site", "timing": "1.", "notes": "trade: second" }
  ],
  "notes": "Wspólne notatki zespołu"
}
```

- Wymagany jest tylko `title`; pozostałe pola pomiń, jeśli niepotrzebne.
- Pusty slot: wpisz `null` (np. `"B": null`) — strona pokaże „Brak strategii”.
- `"example": true` dodaje plakietkę PRZYKŁAD. Usuń to pole, gdy wpiszesz własną strategię.
- Kolejność wierszy w `assignments` = kolejność w tabeli (np. kolejność wejścia).
- `role` to id roli z `data/team.json` — nazwisko gracza strona dobiera sama.
- **Backup:** narysuj plan w dowolnym programie (Excalidraw, Paint, edytor taktyk), zapisz jako PNG w `assets/tactics/<mapa>/backup.png` i wpisz ścieżkę w `"image"`.
- **Podmiana screenshotu:** nadpisz plik pod tą samą nazwą albo zmień ścieżkę `"image"`.

## Gracze, role i rezerwowi (`data/team.json`)

```json
{
  "roles":   [{ "id": "entry", "name": "Entry" }],
  "players": [{ "id": "p1", "name": "Kuba", "role": "entry", "status": "active" }]
}
```

- `status`: `"active"` (skład) albo `"sub"` (rezerwowy). Liczba graczy jest dowolna.
- `id` gracza się nie zmienia (od niego zależą foldery lineupów i notatki). Zmiana nicku = zmiana `name`.
- **Rezerwowy wchodzi za gracza:** ustaw rezerwowemu `"role": "entry"`, a zastępowanemu `"role": null`. Tabele na wszystkich mapach zaktualizują się same.
- Rezerwowi mają własne lineupy (folder `assets/lineups/<mapa>/<id>/`) i mogą wybrać siebie w „Kim jestem”.

## Nowa mapa

1. Dopisz do `data/maps.json`: `{ "id": "dust2", "name": "Dust II" }` (id: małe litery, cyfry, `-`).
2. Utwórz `data/dust2.json` — skopiuj `data/mirage.json`, zmień `"id"` na `"dust2"`, wyczyść strategie (`null`) i lineupy (`[]`).
3. Obrazki w `assets/tactics/dust2/` i `assets/lineups/dust2/<id-gracza>/`.
4. `python3 tools/validate.py`, commit, push.

## Prywatne notatki

- Wybierz siebie w „Kim jestem”, a przy każdej strategii, wariancie execute, lineupie i w zakładce **Notatki** pojawi się pole „Moje notatki”.
- Notatki zapisują się automatycznie w **tej przeglądarce na tym urządzeniu** (localStorage). Nie synchronizują się między urządzeniami ani członkami drużyny i nie trafiają do repozytorium.
- Wyczyszczenie danych przeglądarki usuwa notatki. **Eksport notatek** pobiera kopię zapasową (`cs2-notatki-RRRR-MM-DD.json`); **Import notatek** ją wczytuje (np. na innym komputerze).
- Zmiana `id` lineupu lub gracza „odpina” istniejące notatki od tego elementu.

## Linki do konkretnych widoków

Adres strony zapamiętuje widok, np. `…/#mirage/execute/B` albo `…/#mirage/lineupy/p1` — można je wklejać na Discordzie.

## Testy (dla osoby rozwijającej aplikację)

```bash
python3 -m unittest tools/test_validate.py
node --test tools/test_core.mjs
```
````

- [ ] **Step 2: Run all automated checks**

Run:
```bash
python3 tools/validate.py && python3 -m unittest tools/test_validate.py && node --test tools/test_core.mjs
```
Expected: `OK — brak problemów w danych.`, `OK` from unittest, and `# fail 0` from Node.

- [ ] **Step 3: Full browser pass from a subpath**

Start: `python3 -m http.server 8000 --directory "$(dirname "$PWD")"` and open `http://localhost:8000/TacticsCS2/`. Check that:
- `data/*.json` and every image return 200. DevTools → Network shows no request to `http://localhost:8000/data/…` (the root), only `/TacticsCS2/data/…`.
- Every tab renders. Execute A/B and B's empty state work.
- The lightbox opens and closes.
- Lineup filters work.
- Notes save, restore, clear, export and import.
- Deep link `#mirage/lineupy/p2` opens directly. The back button walks the history.
- The console has no errors or warnings on clean data.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "Add Polish README: preview, deploy, adding maps/strategies/lineups, notes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
