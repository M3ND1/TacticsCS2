import json
import shutil
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


def write_file(root, rel, content):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")


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
        write_file(self.root, rel, content)

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

    def test_unknown_strategy_slot_keys(self):
        m = mirage()
        m["strategies"]["pistolowka"] = {"title": "X"}
        m["strategies"]["execute"]["a"] = {"title": "X"}
        self.write("data/mirage.json", m)
        self.assertProblem('nieznany klucz "pistolowka" w "strategies" (dozwolone: pistol, execute, backup)')
        self.assertProblem('nieznany klucz "a" w "strategies.execute" (dozwolone: A, B)')

    def test_map_data_file_case_mismatch(self):
        (self.root / "data/mirage.json").rename(self.root / "data/Mirage.json")
        probs = self.problems()
        self.assertEqual(
            probs,
            ['data/mirage.json: wielkość liter w nazwie pliku nie zgadza się z "data/Mirage.json" '
             "— GitHub Pages rozróżnia wielkość liter"],
        )

    def test_index_file_case_mismatch(self):
        (self.root / "data/team.json").rename(self.root / "data/Team.json")
        self.assertProblem('data/team.json: wielkość liter w nazwie pliku nie zgadza się z "data/Team.json"')

    def test_cli_exit_codes(self):
        ok = subprocess.run([sys.executable, str(VALIDATE), str(self.root)], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        (self.root / "assets/tactics/mirage/pistol.png").unlink()
        bad = subprocess.run([sys.executable, str(VALIDATE), str(self.root)], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("brak pliku obrazka", bad.stdout)


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class GitTrackingTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel, content in (
            ("data/maps.json", {"maps": [{"id": "mirage", "name": "Mirage"}]}),
            ("data/team.json", TEAM),
            ("data/mirage.json", mirage()),
            ("assets/tactics/mirage/pistol.png", ""),
            ("assets/lineups/mirage/p1/window-1920x1080.png", ""),
        ):
            write_file(self.root, rel, content)
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")

    def tearDown(self):
        self._tmp.cleanup()

    def problems(self):
        return v.validate(self.root)

    def test_fully_tracked_repo_is_ok(self):
        self.assertEqual(self.problems(), [])

    def test_untracked_image_is_reported(self):
        git(self.root, "rm", "-q", "--cached", "assets/tactics/mirage/pistol.png")
        self.assertEqual(
            self.problems(),
            ['data/mirage.json: plik "assets/tactics/mirage/pistol.png" nie jest dodany do gita '
             '(git add "assets/tactics/mirage/pistol.png")'],
        )

    def test_untracked_data_file_is_reported(self):
        git(self.root, "rm", "-q", "--cached", "data/mirage.json")
        self.assertEqual(
            self.problems(),
            ['data/mirage.json: plik "data/mirage.json" nie jest dodany do gita (git add "data/mirage.json")'],
        )

    def test_case_only_rename_not_staged_is_reported(self):
        # disk says pistol.png, git still knows Pistol.png
        git(self.root, "rm", "-q", "--cached", "assets/tactics/mirage/pistol.png")
        (self.root / "assets/tactics/mirage/pistol.png").rename(self.root / "assets/tactics/mirage/Pistol.png")
        git(self.root, "add", "assets/tactics/mirage/Pistol.png")
        (self.root / "assets/tactics/mirage/Pistol.png").rename(self.root / "assets/tactics/mirage/pistol.png")
        self.assertEqual(
            self.problems(),
            ['data/mirage.json: git zna plik jako "assets/tactics/mirage/Pistol.png" — zmień nazwę przez: '
             'git mv -f "assets/tactics/mirage/Pistol.png" "assets/tactics/mirage/pistol.png"'],
        )


if __name__ == "__main__":
    unittest.main()
