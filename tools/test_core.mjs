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

test("parseJson reports the position of an invalid escape sequence", () => {
  assert.throws(() => Core.parseJson('{\n  "img": "C:\\img"\n}', "f.json"),
    { message: "f.json: błąd składni JSON — linia 2, kolumna 13" });
  assert.throws(() => Core.parseJson('{"a":"\\u12"}', "f.json"),
    (err) => /^f\.json: błąd składni JSON — linia 1, kolumna \d+$/.test(err.message));
});

test("parseJson still accepts valid escape sequences", () => {
  assert.deepEqual(Core.parseJson('{"a":"x\\n\\u0041"}', "f.json"), { a: "x\nA" });
});

test("checkMap skips reference checks when team data is unusable", () => {
  const data = {
    id: "mirage",
    strategies: { pistol: { title: "P", assignments: [{ role: "entry" }] } },
    lineups: [{ id: "l1", player: "p1", name: "N", target: "T", side: "T", resolution: "1920x1080", image: "a.png" }],
  };
  const broken = Core.checkMap(data, "mirage", { roles: "x", players: 5 }).map((p) => p.message);
  assert.ok(!broken.some((m) => m.includes("nieznana rola") || m.includes("nieznany gracz")), broken.join("\n"));
  // each list is checked on its own: a valid roles list still enables the role check
  const partial = Core.checkMap(data, "mirage", { roles: [], players: 5 }).map((p) => p.message);
  assert.ok(partial.includes('strategia "pistol": nieznana rola "entry" w assignments[0]'), partial.join("\n"));
  assert.ok(!partial.some((m) => m.includes("nieznany gracz")), partial.join("\n"));
});
