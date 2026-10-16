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

Plik `.nojekyll` w katalogu głównym wyłącza przetwarzanie Jekyllem na GitHub Pages — nie usuwaj go.

## Struktura

```
.nojekyll                   wyłącza Jekyll na GitHub Pages (nie usuwaj)
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

### Dodanie lub podmiana screenshotu strategii

1. Zapisz obrazek (PNG/JPG) w `assets/tactics/<mapa>/`, nazwą małymi literami, np. `execute-b.png`.
   Dla **backupu** możesz narysować plan w dowolnym programie (Excalidraw, Paint, edytor taktyk) i zapisać go jako PNG, np. `backup.png`.
2. W `data/<mapa>.json` wpisz ścieżkę w polu `"image"` właściwego slotu (`pistol`, `execute.A`, `execute.B` albo `backup`), np. `"image": "assets/tactics/mirage/execute-b.png"`.
3. `python3 tools/validate.py`, potem `git add`, `git commit`, `git push`.

Podmiana istniejącego screenshotu: nadpisz plik pod tą samą nazwą albo zmień ścieżkę `"image"`.

Obrazki strategii to diagramy / screenshoty taktyczne i **nie mają pola rozdzielczości** (tylko lineupy je mają). Jeśli rozdzielczość ma znaczenie, możesz ją dopisać do nazwy pliku, np. `execute-a-1920x1080.png`.

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
