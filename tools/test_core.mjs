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
      { id: "l1", player: "p9", name: "N", target: "T", side: "t", type: "he", aspect: "1920x1080", image: "/abs.png" },
      { id: "l1", player: "p1", name: "N", side: "T", type: "smoke", aspect: "16:9", resolution: "1920x1080", image: "a.png" },
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
    'lineup "l1": "type" musi być jednym z: smoke, flash, molotov',
    'lineup "l1": "aspect" musi być jednym z: 4:3, 4:3 stretched, 16:9, 21:9',
    'lineup "l1": pole "resolution" nie jest już używane — użyj "aspect"',
    'lineup "l1": ścieżka "image" musi być względna (bez / na początku, bez .., bez http)',
    'zduplikowane id lineupu "l1"',
    'lineup "l1": brak pola "target"',
  ]) assert.ok(msgs.includes(expected), `missing: ${expected}\n got: ${msgs.join("\n")}`);
});

test("parseHash defaults and validates every part", () => {
  const ctx = { mapIds: ["mirage", "dust2"], playerIds: ["p1", "s1"] };
  assert.deepEqual(Core.parseHash("", ctx), { map: "mirage", tab: "pistolowka", player: null });
  assert.deepEqual(Core.parseHash("#nuke/whatever", ctx), { map: "mirage", tab: "pistolowka", player: null });
  assert.deepEqual(Core.parseHash("#dust2/execute-b", ctx), { map: "dust2", tab: "execute-b", player: null });
  assert.deepEqual(Core.parseHash("#dust2/insta", ctx).tab, "insta");
  assert.deepEqual(Core.parseHash("#mirage/lineupy/s1", ctx).player, "s1");
  assert.deepEqual(Core.parseHash("#mirage/lineupy/ghost", ctx).player, null);
  assert.deepEqual(Core.parseHash("#mirage/%E0%A4%A", ctx).tab, "pistolowka");
});

test("parseHash keeps old #<map>/execute/<A|B> links working", () => {
  const ctx = { mapIds: ["mirage", "dust2"], playerIds: [] };
  assert.equal(Core.parseHash("#dust2/execute/b", ctx).tab, "execute-b");
  assert.equal(Core.parseHash("#dust2/execute/A", ctx).tab, "execute-a");
  assert.equal(Core.parseHash("#dust2/execute", ctx).tab, "execute-a");
});

test("buildHash round-trips through parseHash", () => {
  const ctx = { mapIds: ["mirage"], playerIds: ["p1"] };
  assert.equal(Core.buildHash({ map: "mirage", tab: "execute-b", player: null }), "#mirage/execute-b");
  assert.equal(Core.buildHash({ map: "mirage", tab: "lineupy", player: "p1" }), "#mirage/lineupy/p1");
  assert.equal(Core.buildHash({ map: "mirage", tab: "lineupy", player: null }), "#mirage/lineupy");
  assert.equal(Core.buildHash({ map: "mirage", tab: "backup", player: "p1" }), "#mirage/backup");
  for (const h of ["#mirage/execute-a", "#mirage/execute-b", "#mirage/insta", "#mirage/lineupy/p1", "#mirage/notatki"]) {
    assert.equal(Core.buildHash(Core.parseHash(h, ctx)), h);
  }
});

test("noteKey and noteContext (execute tabs keep their old note keys)", () => {
  assert.equal(Core.noteKey("p1", "mirage", "execute-B"), "cs2pb:v1:notes:p1:mirage:execute-B");
  assert.equal(Core.noteContext("pistolowka"), "pistol");
  assert.equal(Core.noteContext("execute-a"), "execute-A");
  assert.equal(Core.noteContext("execute-b"), "execute-B");
  assert.equal(Core.noteContext("backup"), "backup");
  assert.equal(Core.noteContext("insta"), "insta");
  assert.equal(Core.noteContext("notatki"), "map");
});

test("checkMap validates board, radar, spawns and lineup spawn", () => {
  const lineup = { id: "l1", player: "p1", name: "N", target: "T", side: "T", type: "smoke", aspect: "16:9", image: "a.png" };
  const good = {
    title: "X", steps: ["s1", "s2"],
    board: { players: { entry: [[10, 10], [500, 500]] }, grenades: [{ role: "awp", type: "flash", from: [1, 2], to: [3, 4], step: 2 }] },
  };
  const ok = Core.checkMap({
    id: "mirage", radar: { image: "assets/maps/mirage.png", labels: [{ text: "A", at: [1, 2], kind: "site" }] },
    spawns: { T: "t.jpg", CT: "ct.jpg" },
    strategies: { pistol: good, execute: { A: null, B: null }, backup: null },
    lineups: [{ ...lineup, spawn: 3 }],
  }, "mirage", TEAM);
  assert.deepEqual(ok, []);

  const bad = {
    title: "X", steps: ["s1"],
    board: {
      players: { ghost: [[1, 1], [2, 2]], entry: [[1, 1]] },
      grenades: [{ role: "entry", type: "he", from: [1, 2], to: [3, 4000], step: 2 }],
    },
  };
  const msgs = Core.checkMap({
    id: "mirage", radar: { image: "/abs.png", labels: [{ text: "A" }, { text: "B", at: [1, 1], kind: "big" }] },
    spawns: { T: "http://x/t.jpg", X: "x.jpg" },
    strategies: { pistol: bad, execute: { A: null, B: null }, backup: null },
    lineups: [{ ...lineup, spawn: 11 }],
  }, "mirage", TEAM).map((p) => p.message);
  for (const expected of [
    'strategia "pistol": board.players: nieznana rola "ghost"',
    'strategia "pistol": board.players.entry musi być listą co najmniej 2 punktów [x, y] (0–1024)',
    'strategia "pistol": board.grenades[0]: "type" musi być jednym z: smoke, flash, molotov',
    'strategia "pistol": board.grenades[0]: "from" i "to" muszą być punktami [x, y] (0–1024)',
    'strategia "pistol": board.grenades[0]: "step" musi być numerem kroku 1–1',
    'ścieżka "radar.image" musi być względna (bez / na początku, bez .., bez http)',
    'radar.labels[0] musi mieć "text" i punkt "at" [x, y]',
    'radar.labels[1]: "kind" musi być jednym z: site, spawn, callout',
    'ścieżka "spawns.T" musi być względna (bez / na początku, bez .., bez http)',
    'nieznany klucz "X" w "spawns" (dozwolone: T, CT)',
    'lineup "l1": "spawn" musi być liczbą całkowitą 1–10',
  ]) assert.ok(msgs.includes(expected), `missing: ${expected}\n got: ${msgs.join("\n")}`);
  assert.equal(msgs.length, 11, msgs.join("\n"));
});

test("normalizeMap keeps drawable board parts, radar and spawns", () => {
  const m = Core.normalizeMap({
    radar: { image: "r.png", labels: [{ text: "A", at: [1, 1] }, { text: "bad" }] },
    spawns: { T: "t.jpg", CT: "/abs.jpg" },
    strategies: { pistol: { title: "P", board: { players: { entry: [[1, 1], [2, 2]], awp: [[1, 1]] },
      grenades: [{ type: "smoke", from: [1, 1], to: [2, 2] }, { type: "he", from: [1, 1], to: [2, 2] }] } } },
  });
  assert.deepEqual(m.radar, { image: "r.png", labels: [{ text: "A", at: [1, 1] }] });
  assert.deepEqual(m.spawns, { T: "t.jpg" });
  assert.deepEqual(Object.keys(m.strategies.pistol.board.players), ["entry"]);
  assert.equal(m.strategies.pistol.board.grenades.length, 1);
  assert.equal(Core.normalizeMap({}).radar, null);
});

test("instaLineups: one side, spawn order", () => {
  const ls = [
    { id: "a", name: "Okno", side: "T", spawn: 3 },
    { id: "b", name: "Okno", side: "T", spawn: 1 },
    { id: "c", name: "Mid", side: "CT", spawn: 2 },
    { id: "d", name: "Zwykły", side: "T" },
  ];
  assert.deepEqual(Core.instaLineups(ls, "T").map((l) => l.id), ["b", "a"]);
  assert.deepEqual(Core.instaLineups(ls, "CT").map((l) => l.id), ["c"]);
});

test("checkTeam validates player color", () => {
  const msgs = Core.checkTeam({
    roles: [],
    players: [
      { id: "a", name: "A", role: null, status: "active", color: "#4aa8e0" },
      { id: "b", name: "B", role: null, status: "active", color: "blue" },
    ],
  }).map((p) => p.message);
  assert.deepEqual(msgs, ['gracz "b": "color" musi być kolorem w formacie #RRGGBB']);
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

test("formatAspect and aspectMismatch", () => {
  assert.equal(Core.formatAspect("4:3 stretched"), "4:3 rozciągnięte");
  assert.equal(Core.formatAspect("16:9"), "16:9");
  assert.equal(Core.formatAspect(null), "?");
  assert.equal(Core.aspectMismatch("4:3", "16:9"), true);
  assert.equal(Core.aspectMismatch("4:3", "4:3 stretched"), true);
  assert.equal(Core.aspectMismatch("16:9", "16:9"), false);
  assert.equal(Core.aspectMismatch("16:9", null), false);
  assert.equal(Core.aspectMismatch(undefined, "16:9"), false);
});

test("lineupFacets and filterLineups use type, site and side", () => {
  const ls = [
    { id: "a", type: "molotov", site: "B", side: "T", aspect: "21:9" },
    { id: "b", type: "smoke", site: "Mid", side: "CT", aspect: "16:9" },
    { id: "c", type: "smoke", site: "A", side: "T", aspect: "4:3 stretched" },
    { id: "d", type: "smoke", side: "T", aspect: "16:9" },
  ];
  assert.deepEqual(Core.lineupFacets(ls), { types: ["smoke", "molotov"], sites: ["A", "B", "Mid"], sides: ["T", "CT"] });
  assert.deepEqual(Core.filterLineups(ls, { type: "smoke", site: null, side: null }).map((l) => l.id), ["b", "c", "d"]);
  assert.deepEqual(Core.filterLineups(ls, { type: null, site: null, side: "T" }).map((l) => l.id), ["a", "c", "d"]);
  assert.deepEqual(Core.filterLineups(ls, { type: "smoke", site: "A", side: null }).map((l) => l.id), ["c"]);
  assert.deepEqual(Core.filterLineups(ls, { type: null, site: "B", side: "T" }).map((l) => l.id), ["a"]);
  assert.deepEqual(Core.filterLineups(ls, {}).map((l) => l.id), ["a", "b", "c", "d"]);
});

test("checkMap validates optional lineup site", () => {
  const base = { id: "l1", player: "p1", name: "N", target: "T", side: "T", type: "smoke", aspect: "16:9", image: "a.png" };
  const data = {
    id: "mirage",
    strategies: { pistol: null, execute: { A: null, B: null }, backup: null },
    lineups: [{ ...base, site: "A" }, { ...base, id: "l2", site: "Mid" }, { ...base, id: "l3" }, { ...base, id: "l4", site: "a" }],
  };
  const msgs = Core.checkMap(data, "mirage", TEAM).map((p) => p.message);
  assert.deepEqual(msgs, ['lineup "l4": "site" musi być jednym z: A, B, Mid']);
});

test("utilityTokens colours grenade words", () => {
  assert.deepEqual(Core.utilityTokens("2× flash + smoke'a, molo na site"), [
    { text: "2× ", type: null },
    { text: "flash", type: "flash" },
    { text: " + ", type: null },
    { text: "smoke'a", type: "smoke" },
    { text: ", ", type: null },
    { text: "molo", type: "molotov" },
    { text: " na site", type: null },
  ]);
  assert.deepEqual(Core.utilityTokens("Flashe i Molotov, incendiary"), [
    { text: "Flashe", type: "flash" },
    { text: " i ", type: null },
    { text: "Molotov", type: "molotov" },
    { text: ", ", type: null },
    { text: "incendiary", type: "molotov" },
  ]);
  assert.deepEqual(Core.utilityTokens(""), []);
  assert.deepEqual(Core.utilityTokens("brak"), [{ text: "brak", type: null }]);
});

test("checkTeam validates player aspect", () => {
  const msgs = Core.checkTeam({
    roles: [],
    players: [
      { id: "a", name: "A", role: null, status: "active", aspect: "4:3 stretched" },
      { id: "b", name: "B", role: null, status: "active", aspect: null },
      { id: "c", name: "C", role: null, status: "sub", aspect: "16x9" },
    ],
  }).map((p) => p.message);
  assert.deepEqual(msgs, ['gracz "c": "aspect" musi być jednym z: 4:3, 4:3 stretched, 16:9, 21:9 albo null']);
});

test("checkMapsIndex validates accent and mapAccent returns safe colours", () => {
  assert.deepEqual(Core.checkMapsIndex({ maps: [{ id: "a", name: "A", accent: "#12abEF" }] }), []);
  const msgs = Core.checkMapsIndex({ maps: [{ id: "a", name: "A", accent: "red; x" }] }).map((p) => p.message);
  assert.deepEqual(msgs, ['mapa "a": "accent" musi być kolorem w formacie #RRGGBB']);
  assert.equal(Core.mapAccent({ accent: "#12abEF" }), "#12abEF");
  assert.equal(Core.mapAccent({ accent: "red; x" }), null);
  assert.equal(Core.mapAccent(undefined), null);
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
    lineups: [{ id: "l1", player: "p1", name: "N", target: "T", side: "T", type: "smoke", aspect: "16:9", image: "a.png" }],
  };
  const broken = Core.checkMap(data, "mirage", { roles: "x", players: 5 }).map((p) => p.message);
  assert.ok(!broken.some((m) => m.includes("nieznana rola") || m.includes("nieznany gracz")), broken.join("\n"));
  // each list is checked on its own: a valid roles list still enables the role check
  const partial = Core.checkMap(data, "mirage", { roles: [], players: 5 }).map((p) => p.message);
  assert.ok(partial.includes('strategia "pistol": nieznana rola "entry" w assignments[0]'), partial.join("\n"));
  assert.ok(!partial.some((m) => m.includes("nieznany gracz")), partial.join("\n"));
});

test("checkMap flags unknown strategy slot keys", () => {
  const data = {
    id: "mirage",
    strategies: { pistolowka: { title: "P" }, pistol: null, execute: { a: { title: "X" }, A: null, B: null }, backup: null },
    lineups: [],
  };
  const msgs = Core.checkMap(data, "mirage", TEAM).map((p) => p.message);
  assert.ok(msgs.includes('nieznany klucz "pistolowka" w "strategies" (dozwolone: pistol, execute, backup)'), msgs.join("\n"));
  assert.ok(msgs.includes('nieznany klucz "a" w "strategies.execute" (dozwolone: A, B)'), msgs.join("\n"));
  const ok = Core.checkMap({ id: "mirage", strategies: { pistol: null, execute: { A: null, B: null }, backup: null }, lineups: [] }, "mirage", TEAM);
  assert.deepEqual(ok, []);
});
