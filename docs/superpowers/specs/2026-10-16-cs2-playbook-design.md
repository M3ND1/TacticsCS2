# CS2 Team Playbook — Design

Date: 2026-10-16
Status: Approved in brainstorming, pending spec review

## 1. Purpose

A private, static reference site for our own CS2 team. It helps us memorize team
strategies, each player's responsibilities, and personal smoke lineups.

Not a SaaS product, social platform, or tactical editor. No accounts, no backend,
no database, no build step, no in-app editing of shared data.

### Success criteria

- Opening the site shows a map selector, three strategy slots, a lineup section,
  and a map-notes section without any instructions needed.
- Adding a lineup = copy one screenshot into the right folder + add one JSON entry
  + commit + push. Nothing else.
- Adding a map = add one line to `data/maps.json` + create `data/<map>.json` + assets.
- A substitute can take over a role by editing only `data/team.json`.
- Broken data (bad JSON, missing image, unknown role/player id) is visible and names
  the exact file/path/id, never a silent blank.
- Works on GitHub Pages served from a repository subpath (`/<repo>/`).

### Non-goals

- No drawing engine (Backup diagrams are pre-drawn images).
- No writing to repository files from the browser.
- No sync of personal notes between devices or teammates.
- No support for opening `index.html` via `file://`.

## 2. Language

- UI labels: Polish. Standard CS2 terms stay English where that is natural usage
  (smoke, flash, molotov, entry, execute, lineup, AWP, T/CT).
- `README.md`: Polish.
- Strategy/lineup content: whatever language the team writes in JSON.

## 3. Repository layout

```
index.html                     all HTML, CSS, JS (single file, no dependencies)
.nojekyll                      disable Jekyll processing on GitHub Pages
README.md                      Polish: local preview, deploy, how to add content
data/
  maps.json                    ordered list of maps
  team.json                    roles + players (shared roster)
  mirage.json                  strategies + lineups for Mirage
assets/
  tactics/<mapId>/pistol.<ext>, execute-a.<ext>, execute-b.<ext>, backup.<ext>
  lineups/<mapId>/<playerId>/<descriptive-name>-<WIDTHxHEIGHT>.<ext>
tools/
  validate.py                  stdlib-only data checker, run before pushing
  test_validate.py             unit tests for the checker
docs/superpowers/specs/        design docs
```

Filename conventions are recommendations; the JSON path is the source of truth.
Lineup filenames should include the resolution (e.g. `window-t-spawn-1920x1080.png`).

All URLs in code and JSON are relative to `index.html` (no leading `/`).

## 4. Data model

### 4.1 `data/maps.json`

```json
{
  "maps": [
    { "id": "mirage", "name": "Mirage" }
  ]
}
```

- Order in the array = order in the map selector.
- Map data is loaded from `data/<id>.json`.
- `id`: lowercase `[a-z0-9-]+`, unique.

### 4.2 `data/team.json`

```json
{
  "roles": [
    { "id": "entry", "name": "Entry" },
    { "id": "awp",   "name": "AWP" }
  ],
  "players": [
    { "id": "p1", "name": "PRZYKŁAD Gracz 1", "role": "entry", "status": "active" },
    { "id": "s1", "name": "PRZYKŁAD Rezerwa 1", "role": null,   "status": "sub" }
  ]
}
```

- Any number of roles and players; no five-player limit anywhere.
- `status`: `"active"` or `"sub"`.
- `role`: a role id or `null`.
- Player `id` is stable: it keys lineups, lineup folders, and personal notes.
  Renaming a player means changing `name` only.

**Role resolution** (used by strategy tables): for role R, show the active player
whose `role` is R; if none, a sub whose `role` is R (labelled "rezerwa"); if none,
show `— brak gracza` in a warning colour. If more than one player of the same status
holds R, show all of them and raise a data warning.

Substitution: set the sub's `role` to the role, set the replaced player's `role` to
`null`. No map file changes.

### 4.3 `data/<mapId>.json`

```json
{
  "id": "mirage",
  "name": "Mirage",
  "strategies": {
    "pistol":  { /* Strategy */ },
    "execute": { "A": { /* Strategy */ }, "B": null },
    "backup":  { /* Strategy */ }
  },
  "lineups": [ /* Lineup */ ]
}
```

- `id` must equal the id in `maps.json` (warning otherwise).
- The three slots are fixed: `pistol`, `execute` (with `A` and `B`), `backup`.
- A slot or variant that is `null` or missing renders an empty state
  ("Brak strategii" / "Brak strategii dla B"). Content is never copied between A and B.

**Strategy**

| Field         | Type                | Required | Notes |
|---------------|---------------------|----------|-------|
| `title`       | string              | yes      | |
| `example`     | boolean             | no       | `true` shows a PRZYKŁAD badge |
| `summary`     | string              | no       | Description; line breaks preserved |
| `image`       | string (path)       | no       | Tactical screenshot or pre-drawn diagram |
| `steps`       | string[]            | no       | Rendered as an ordered list |
| `assignments` | Assignment[]        | no       | Rendered as a table |
| `notes`       | string              | no       | Shared team notes |

**Assignment** (one table row)

| Field      | Type   | Required | Column    |
|------------|--------|----------|-----------|
| `role`     | string | yes      | Rola + Gracz (resolved) |
| `position` | string | no       | Pozycja   |
| `utility`  | string | no       | Utility   |
| `action`   | string | no       | Zadanie   |
| `timing`   | string | no       | Timing    |
| `notes`    | string | no       | Uwagi     |

Table rows render in array order (this is the entry/trade order when relevant).

**Lineup**

| Field          | Type   | Required | Notes |
|----------------|--------|----------|-------|
| `id`           | string | yes      | Unique within the map; keys personal notes |
| `player`       | string | yes      | Player id from `team.json` |
| `name`         | string | yes      | e.g. "Window" |
| `target`       | string | yes      | Where the smoke lands |
| `side`         | string | yes      | `"T"` or `"CT"` |
| `from`         | string | no       | Starting position |
| `resolution`   | string | yes      | e.g. `"1920x1080"` |
| `aspect`       | string | no       | e.g. `"16:9"`, `"4:3"` |
| `image`        | string | yes      | Screenshot path |
| `throw`        | string | no       | e.g. "jumpthrow", "left click" |
| `instructions` | string | no       | |
| `notes`        | string | no       | Shared practice notes |
| `example`      | bool   | no       | PRZYKŁAD badge |

Text fields are rendered as plain text (escaped), never as HTML.

## 5. UI

### 5.1 Layout (desktop-first; usable down to ~1000px, stacks below that)

```
Header:   CS2 PLAYBOOK   [map selector buttons]          Kim jestem: [select]  Eksport | Import
Tabs:     Pistolówka | Execute | Backup  ‖  Lineupy | Notatki
Body:     depends on tab
Bottom:   collapsible data-problems bar (only if problems exist)
```

### 5.2 Strategy tabs (Pistolówka, Execute, Backup)

- Execute only: segmented control `[ A | B ]` above the content.
- Title + PRZYKŁAD badge if `example`.
- Two columns: image on the left (whole image visible, `object-fit: contain`,
  click opens lightbox); summary and numbered steps on the right.
- Assignment table full width: Rola | Gracz | Pozycja | Utility | Zadanie | Timing | Uwagi.
- Shared notes ("Notatki zespołu").
- Personal notes ("Moje notatki") for this context.
- Missing optional fields are simply omitted (no empty headings).

### 5.3 Lineupy tab

- Left: player list grouped "Skład" (active) then "Rezerwowi" (subs), each with
  their lineup count for this map. Default selection: the "Kim jestem" player, else
  the first active player.
- Filters: side chips (T / CT) and resolution chips. Only values present in the
  selected player's lineups are shown; filters hidden if only one value exists.
- One row per lineup: thumbnail (contain, fixed max height ~220px) + name, target,
  side, from, throw, a prominent resolution label "1920×1080 · 16:9",
  instructions, shared notes, and personal notes for `lineup:<id>`.
- Empty state: "Brak lineupów dla <gracz> na <mapa>".

### 5.4 Notatki tab

Personal map-wide notes (`map` context) for the current player.

### 5.5 Shared behaviour

- **Lightbox**: any screenshot opens full-viewport, scaled to fit. Closes on Esc,
  click, or close button. Shows the image path and (for lineups) resolution.
- **URL hash** routing: `#<mapId>/<tab>[/<variant-or-player>]`, e.g.
  `#mirage/execute/B`, `#mirage/lineupy/p1`. Tab slugs: `pistolowka`, `execute`,
  `backup`, `lineupy`, `notatki`. Unknown hash → first map, first tab. Back/forward work.
- **Missing image**: dark box with red border, text `Brak pliku:` + path.
- **Style**: background `#16181b`, panels `#1c1f23`, borders `#2a2d31`, text `#d7dadf`,
  muted text `#8a9099`, accent `#6a9f5b`, warning `#d29a3a`, error `#d0544f`.
  System font stack, 13–14px. No cards, gradients, shadows, or animations.

## 6. Personal notes (localStorage)

- Current player: key `cs2pb:v1:me` → player id. Picker lists active players, then
  subs in an optgroup "Rezerwowi". If the stored id no longer exists, reset to none.
- Note key: `cs2pb:v1:notes:<playerId>:<mapId>:<context>` where context is one of
  `map`, `pistol`, `execute-A`, `execute-B`, `backup`, `lineup:<lineupId>`.
- No player selected → note fields disabled with hint
  "Wybierz gracza w „Kim jestem”, aby pisać notatki".
- Autosave 400 ms after the last keystroke, and on blur. Status text:
  `✓ zapisano` / `✗ nie zapisano — pamięć przeglądarki niedostępna`.
  Empty (whitespace-only) note removes the key.
- "Wyczyść" → inline confirm "Na pewno? Tak / Nie" (no browser dialogs).
- Export: downloads `cs2-notatki-YYYY-MM-DD.json`:
  `{ "app": "cs2-playbook", "version": 1, "exportedAt": "<ISO>", "notes": { "<key>": "<text>" } }`
  containing every `cs2pb:v1:notes:*` key on this device.
- Import: file picker; reject anything not matching that format or with non-string
  values or keys outside the `cs2pb:v1:notes:` prefix; merge (imported wins on the
  same key); report "Zaimportowano N notatek" or the specific error inline.
- All localStorage access is wrapped in try/catch; failures show the status text,
  never break rendering.
- No other UI preferences are stored; view state lives in the URL hash.

## 7. Loading and error handling

- Load order: `maps.json` and `team.json` in parallel; then the selected map's file
  (fetched on demand, cached in memory for the session).
- All fetches use relative URLs and `{ cache: "no-cache" }` so a push is visible
  without a hard refresh.
- Each file is fetched as text and parsed with `JSON.parse`; on syntax error, the
  error shows the file path plus line and column (computed from the error position).
- `maps.json` or `team.json` failure → full-page error naming the file and reason
  (HTTP status, network error, or syntax position). Nothing partial renders.
- Map file failure → error in the content area naming the file; header and other
  maps remain usable.
- `location.protocol === "file:"` → full-page message with the local-server command.
- Data checks at load (no network): required fields, `side` values, `status` values,
  role ids in assignments, player ids in lineups, duplicate ids, map id mismatch,
  multiple holders of a role. Problems → collapsible bar "⚠ N problemów w danych"
  listing `file: message`, also `console.warn`. Rendering continues with inline ⚠
  markers where the bad reference appears.
- Images: `onerror` swaps in the missing-file placeholder.

## 8. Example content

- `team.json`: example roles (Entry, Second, Support, Lurk, AWP) and players
  "PRZYKŁAD Gracz 1…5" plus one "PRZYKŁAD Rezerwa 1".
- `mirage.json`: all strategies and lineups `"example": true`, with generic
  placeholder text that explicitly says to replace it (no real tactics).
  Execute A filled, Execute B `null` (demonstrates the empty state).
- Placeholder images: simple SVGs that read "PRZYKŁAD — podmień na własny
  screenshot" with the intended filename/resolution. Real screenshots will be PNG/JPG.

## 9. Validation tool (`tools/validate.py`)

Python 3 standard library only. Run `python3 tools/validate.py` from the repo root.
Checks the same rules as the in-app checks plus:

- Every referenced image exists **with exact filename case** (GitHub Pages is
  case-sensitive; macOS is not).
- Every map in `maps.json` has a data file.
- Paths are relative (no leading `/`, no `..`, no `http`).

Exit code 0 when clean, 1 with a list of `file: problem` lines otherwise.
Unit tests in `tools/test_validate.py` (`python3 -m unittest tools/test_validate.py`).

## 10. Verification before completion

1. `python3 tools/validate.py` passes on the shipped example data.
2. `python3 -m unittest tools/test_validate.py` passes.
3. Serve the parent directory and open `http://localhost:8000/TacticsCS2/` (subpath)
   in a browser; verify: map loads, all five tabs, A/B toggle with B empty state,
   lightbox open/close, lineup filters, missing-image placeholder (temporary bad path),
   bad JSON error message (temporary syntax error), notes save/restore/clear across
   reload, per-player separation, export and import round-trip, hash deep links and
   back button. No console errors on the clean data.

## 11. Deployment

GitHub repo → Settings → Pages → Deploy from branch → `main` / `(root)`.
`.nojekyll` at the root. README (Polish) documents this, local preview via
`python3 -m http.server 8000`, and step-by-step: add a map, add/replace a strategy
screenshot, add a lineup, add a player or swap in a substitute, and the note that
personal notes live only in the current browser/device.
