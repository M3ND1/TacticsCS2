# CS2 Playbook

Prywatna ściąga taktyczna naszej drużyny CS2: trzy strategie na mapę (pistolówka, execute A/B, backup), zadania graczy oraz osobiste lineupy smoke'ów.

Strona jest w pełni statyczna: jeden plik `index.html` + dane w `data/*.json` + obrazki w `assets/`. Nie ma backendu, bazy danych ani kont.

> **Uwaga o prywatności:** strona na GitHub Pages jest publicznie dostępna pod swoim adresem — każdy, kto zna link, może ją otworzyć (strona ma `noindex`, więc nie trafi do wyszukiwarek). GitHub Pages z **prywatnego** repozytorium wymaga płatnego planu (GitHub Pro/Team/Enterprise); na darmowym GitHub Free repozytorium musi być **publiczne**, a wtedy wszystkie JSON-y, screenshoty i dokumenty są widoczne także na github.com, nie tylko pod adresem strony. Nie wrzucaj tu niczego, czego nie chcesz pokazać.

## Uruchomienie lokalne

Otwarcie `index.html` podwójnym kliknięciem **nie zadziała** (przeglądarka blokuje wczytywanie JSON z `file://`). W folderze repozytorium uruchom:

```bash
python3 -m http.server 8000     # Windows: py -m http.server 8000
```

i otwórz <http://localhost:8000>.

## Publikacja (GitHub Pages)

1. Wypchnij repozytorium na GitHub. Pamiętaj: na GitHub Free Pages działa tylko z **publicznego** repozytorium (prywatne wymaga planu Pro/Team/Enterprise) — patrz uwaga o prywatności wyżej.
2. **Settings → Pages → Build and deployment → Deploy from a branch**, gałąź `main`, folder `/ (root)`.
3. Po minucie strona będzie pod `https://<użytkownik>.github.io/<repozytorium>/`.

Każdy kolejny `git push` aktualizuje stronę (zwykle w ciągu 1–2 minut). Wszystkie ścieżki są względne, więc działa to też z podkatalogu repozytorium.

Plik `.nojekyll` w katalogu głównym wyłącza przetwarzanie Jekyllem na GitHub Pages — nie usuwaj go.

## Struktura

```
.nojekyll                   wyłącza Jekyll na GitHub Pages (nie usuwaj)
index.html                  aplikacja (nie trzeba jej edytować przy dodawaniu treści)
data/maps.json              lista map i ich kolejność
data/team.json              role i gracze (skład + rezerwowi)
data/<mapa>.json            strategie i lineupy dla mapy
assets/maps/<mapa>.png      radar mapy (podkład tablicy taktycznej)
assets/spawns/<mapa>/T.jpg, CT.jpg   screeny ponumerowanych spawnów (zakładka Insta smoke)
assets/tactics/<mapa>/      screenshoty / diagramy strategii
assets/lineups/<mapa>/<id-gracza>/   screenshoty lineupów
tools/validate.py           sprawdzanie danych przed pushem
```

## Przed każdym pushem

```bash
python3 tools/validate.py       # Windows: py tools/validate.py
```

(W kolejnych krokach `python3` zamień na `py`, jeśli jesteś na Windows.)

Sprawdza składnię JSON, odwołania do ról i graczy, unikalność id, czy każdy obrazek istnieje **i czy wielkość liter w nazwie pliku się zgadza**. macOS i Windows ignorują wielkość liter, GitHub Pages nie — `Window.png` ≠ `window.png`. Najprościej: kopiuj nazwę pliku do JSON-a znak w znak, bez spacji i polskich liter.

Walidator sprawdza też (gdy folder jest repozytorium git), czy każdy plik danych i obrazek jest **dodany do gita** pod dokładnie tą nazwą — na GitHub trafia tylko to, co git śledzi. Plik, którego nazwę zmieniono tylko wielkością liter (np. `Stara.png` → `stara.png`), na macOS i Windows wymaga `git mv -f Stara.png stara.png`, inaczej git zachowa starą nazwę. Nowe screenshoty trzeba dodać przez `git add`.

Problemy w danych widać też na stronie — pasek „⚠ N problemów w danych” na dole ekranu.

## Dodanie lineupu — smoke, flash, molotov (najczęstsza czynność)

Wszystkie mapy i foldery graczy już istnieją (`assets/lineups/<mapa>/<gracz>/`). Dodajesz tylko zdjęcie i jeden wpis:

1. Zrób screenshot w grze (Steam F12 zapisuje JPG). Zapisz go jako np.
   `assets/lineups/mirage/mendi/Mid-smoke-okno.jpg`
   (folder = id mapy / id gracza; nazwa pliku: `Rejon-typ-cel.jpg`).
2. Dopisz wpis do `"lineups"` w `data/mirage.json`:

   ```json
   {
     "id": "mid-okno",
     "player": "mendi",
     "type": "smoke",
     "name": "Mid okno",
     "target": "Okno",
     "side": "T",
     "site": "Mid",
     "from": "T spawn",
     "throw": "jumpthrow",
     "aspect": "16:9",
     "image": "assets/lineups/mirage/mendi/Mid-smoke-okno.jpg",
     "instructions": "Stań w rogu przy ...",
     "notes": ""
   }
   ```

   Wymagane: `id`, `player`, `type`, `name`, `target`, `side` (`T` albo `CT`), `aspect`, `image`. Reszta jest opcjonalna.
   - `type`: `"smoke"` (szary), `"flash"` (żółty) albo `"molotov"` (czerwony).
   - `site`: rejon mapy — `"A"`, `"B"` albo `"Mid"`. Po nim działa filtr „Rejon” na liście lineupów; lineup bez `site` widać tylko przy „Wszystkie”.
   - `aspect`: proporcje ekranu, pod które działa lineup: `"4:3"`, `"4:3 stretched"` (rozciągnięte), `"16:9"` albo `"21:9"`. Rozdzielczość w pikselach (1080p, 1440p, 4K) nie ma znaczenia — liczą się proporcje.
   - `id` musi być unikalne w obrębie mapy — przypisane są do niego prywatne notatki, więc lepiej go potem nie zmieniać.
3. `python3 tools/validate.py`, potem `git add`, `git commit`, `git push`.

Samo skopiowanie obrazka do folderu **nie** wystarczy — strona statyczna nie widzi zawartości folderów, dlatego każdy obrazek musi mieć wpis w JSON.

Lista lineupów gracza ma filtry: **Typ** (smoke / flash / molotov), **Rejon** (A / B / Mid) i **Strona** (T / CT).

Ten sam lineup pod inne proporcje = osobny wpis z innym `id`, `aspect` i plikiem.

Gdy wybierzesz siebie w „Kim jestem”, przy lineupach pod inne proporcje niż Twoje zobaczysz ostrzeżenie „może nie wejść”.

## Insta smoke (zakładka na każdej mapie)

Zakładka **Insta smoke** pokazuje screen ponumerowanych spawnów T i CT oraz lineupy rzucane od razu ze spawnu, ułożone wg numeru.

- Screen spawnów: zapisz jako `assets/spawns/<mapa>/T.jpg` / `CT.jpg` i wpisz w `data/<mapa>.json` (obok `"name"`):
  `"spawns": { "T": "assets/spawns/mirage/T.jpg", "CT": "assets/spawns/mirage/CT.jpg" }`.
- Lineup jest insta smoke'iem, gdy ma pole `"spawn"` — numer pozycji na spawnie (1–10), np. `"spawn": 3`. Taki lineup widać też normalnie w zakładce Lineupy.

## Strategie (pistolówka, execute A, execute B, backup)

Każda mapa ma dokładnie trzy sloty w `"strategies"`: `pistol`, `execute` (z wariantami `A` i `B` — na stronie to osobne zakładki „Execute A” i „Execute B”) oraz `backup` (inne klucze, np. literówka `pistolowka`, walidator zgłasza jako błąd). Każda strategia ma ten sam format:

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

### Dodanie lub podmiana screenshotu strategii

1. Zapisz obrazek (PNG/JPG) w `assets/tactics/<mapa>/`, nazwą małymi literami, np. `execute-b.png`.
   Dla **backupu** możesz narysować plan w dowolnym programie (Excalidraw, Paint, edytor taktyk) i zapisać go jako PNG, np. `backup.png`.
2. W `data/<mapa>.json` wpisz ścieżkę w polu `"image"` właściwego slotu (`pistol`, `execute.A`, `execute.B` albo `backup`), np. `"image": "assets/tactics/mirage/execute-b.png"`.
3. `python3 tools/validate.py`, potem `git add`, `git commit`, `git push`.

Podmiana istniejącego screenshotu: nadpisz plik pod tą samą nazwą albo zmień ścieżkę `"image"`.

### Tablica taktyczna (radar z trasami i granatami)

Strategia z polem `"board"` zamiast obrazka pokazuje tablicę w stylu cs2strats: radar mapy, trasy graczy w ich kolorach, granaty z linią rzutu i nickiem rzucającego. Kliknięcie kroku podświetla granaty z tego kroku. Nicki i kolory strona bierze z ról w `data/team.json`, więc zmiana ról niczego nie psuje.

Mapa musi mieć radar (obok `"name"` w `data/<mapa>.json`):

```json
"radar": {
  "image": "assets/maps/mirage.png",
  "labels": [{ "text": "A", "at": [556, 792], "kind": "site" }, { "text": "Mid", "at": [575, 505] }]
}
```

Tablica w strategii:

```json
"board": {
  "players": { "entry": [[900, 368], [848, 625], [705, 662], [600, 742]] },
  "grenades": [{ "role": "second", "type": "smoke", "from": [848, 625], "to": [415, 800], "step": 2 }]
}
```

- Współrzędne to piksele radaru `[x, y]`, od 0 do 1024. **Kliknij mapę na stronie** — pod tablicą pojawi się punkt `[x, y]` do wklejenia.
- `players`: trasa każdej roli (co najmniej 2 punkty); żeton z nickiem stoi na końcu trasy.
- `grenades`: `type` = `smoke` / `flash` / `molotov`, `from` = skąd rzut, `to` = gdzie ląduje, `step` = numer kroku (opcjonalny).
- `labels`: `kind` = `site` (duża litera), `spawn` albo `callout` (mały podpis, domyślnie).
- Radary pochodzą z plików gry (repozytorium [MurkyYT/cs2-map-icons](https://github.com/MurkyYT/cs2-map-icons), `de_<mapa>_radar_psd.png`).

Obrazki strategii to diagramy / screenshoty taktyczne i **nie mają pola proporcji** (tylko lineupy je mają). Jeśli ma to znaczenie, dopisz proporcje do nazwy pliku, np. `execute-a-16x9.png`.

W kolumnie **Utility**, w opisie i w krokach słowa smoke…, flash…, molo… / molotov i incendiary same dostają kolor (smoke niebieski, flash żółty, molotov czerwony), a nicki graczy — kolor gracza.

## Gracze, role i rezerwowi (`data/team.json`)

```json
{
  "roles":   [{ "id": "entry", "name": "Entry" }],
  "players": [{ "id": "mendi", "name": "Mendi", "role": "entry", "status": "active", "aspect": "16:9", "color": "#4cd964", "short": "M" }]
}
```

- `color`: kolor gracza — na tablicy taktycznej, przy nicku w tabelach, na liście graczy w Lineupach i w krokach taktyk (`#RRGGBB`, opcjonalny).
- `short`: skrót gracza (1–3 znaki) na żetonach tablicy taktycznej, np. `"M"` (opcjonalny; bez niego dwie pierwsze litery nicku).
- `status`: `"active"` (skład) albo `"sub"` (rezerwowy). Liczba graczy jest dowolna.
- `aspect`: proporcje ekranu gracza — `"4:3"`, `"4:3 stretched"`, `"16:9"`, `"21:9"` albo `null` (nieustawione, na stronie widać „?”). Widać je przy nicku w tabelach, na liście lineupów i w „Kim jestem” — reszta drużyny od razu wie, że ktoś gra na innych proporcjach i jego instant smoke może u nich nie wejść.
- Role w `data/team.json` są na razie przykładowe — ustaw własne.
- `id` gracza się nie zmienia (od niego zależą foldery lineupów i notatki). Zmiana nicku = zmiana `name`.
- **Rezerwowy wchodzi za gracza:** ustaw rezerwowemu `"role": "entry"`, a zastępowanemu `"role": null`. Tabele na wszystkich mapach zaktualizują się same.
- Rezerwowi mają własne lineupy (folder `assets/lineups/<mapa>/<id>/`) i mogą wybrać siebie w „Kim jestem”.

## Nowa mapa

Gotowe są: Mirage, Dust II, Inferno, Ancient, Nuke, Anubis i Cache (każda ma własny kolor `"accent"` w `data/maps.json`). Kolejną, np. Train, dodajesz tak:

1. Dopisz do tablicy `"maps"` w `data/maps.json` nowy wpis `{ "id": "train", "name": "Train", "accent": "#8a8fc9" }` (po przecinku po poprzednim wpisie; id: małe litery, cyfry, `-`; `accent` — kolor motywu mapy w formacie `#RRGGBB`, opcjonalny).
2. Utwórz `data/train.json` — skopiuj `data/nuke.json` i zmień `"id"` i `"name"`. Pusty szkielet wygląda tak:

   ```json
   "strategies": { "pistol": null, "execute": { "A": null, "B": null }, "backup": null }, "lineups": []
   ```
3. Obrazki w `assets/tactics/train/` i `assets/lineups/train/<id-gracza>/`.
4. `python3 tools/validate.py`, commit, push.

## Prywatne notatki

- Wybierz siebie w „Kim jestem”, a przy każdej strategii, lineupie i w zakładce **Notatki** pojawi się pole „Moje notatki”.
- Notatki zapisują się automatycznie w **tej przeglądarce na tym urządzeniu** (localStorage). Nie synchronizują się między urządzeniami ani członkami drużyny i nie trafiają do repozytorium.
- Wyczyszczenie danych przeglądarki usuwa notatki. **Eksport notatek** pobiera kopię zapasową (`cs2-notatki-RRRR-MM-DD.json`); **Import notatek** ją wczytuje (np. na innym komputerze).
- Notatki są przypisane do **adresu strony**: te zapisane na `localhost` nie pojawią się na `github.io` (i odwrotnie). Przenieś je eksportem i importem.
- Zmiana `id` lineupu lub gracza „odpina” istniejące notatki od tego elementu.

## Linki do konkretnych widoków

Adres strony zapamiętuje widok, np. `…/#mirage/execute-b`, `…/#ancient/insta` albo `…/#mirage/lineupy/mendi` — można je wklejać na Discordzie. Stare linki `…/#mirage/execute/B` nadal działają.

## Testy (dla osoby rozwijającej aplikację)

```bash
python3 -m unittest tools/test_validate.py      # Windows: py -m unittest tools/test_validate.py
node --test tools/test_core.mjs
```
