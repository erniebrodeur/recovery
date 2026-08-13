from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "journal" / "scripts" / "journal_store.py"


class JournalStoreTests(unittest.TestCase):
    def run_store(self, *args: str, input_text: str = "", expected: int = 0):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(expected, completed.returncode, completed.stderr)
        stream = completed.stdout if completed.returncode == 0 else completed.stderr
        return json.loads(stream)

    def test_platform_detection_and_destinations(self):
        posix = self.run_store("resolve-directory", "--cwd", "/work/recovery", "--home", "/people/test")
        self.assertEqual("posix", posix["platform"])
        self.assertEqual("/people/test/Documents/recovery-journals", posix["directory"])

        windows = self.run_store(
            "resolve-directory",
            "--cwd",
            r"C:\work\recovery",
            "--home",
            r"C:\Users\Test",
        )
        self.assertEqual("windows", windows["platform"])
        self.assertEqual(r"C:\Users\Test\Documents\Recovery Journal", windows["directory"])

        ambiguous = self.run_store("resolve-directory", "--cwd", "relative/project", expected=2)
        self.assertIn("ambiguous", ambiguous["error"])

    def test_save_requires_permission_and_first_save_warning(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "journals"
            args = (
                "append",
                "--directory",
                str(directory),
                "--date",
                "2026-08-13",
                "--time",
                "09:00:00",
            )
            self.run_store(*args, input_text="Draft", expected=2)
            self.assertFalse(directory.exists())

            self.run_store(*args, "--confirmed-save", input_text="Draft", expected=2)
            self.assertFalse(directory.exists())

            saved = self.run_store(
                *args,
                "--confirmed-save",
                "--plaintext-warning-shown",
                input_text="First entry",
            )
            self.assertEqual("appended", saved["action"])
            self.assertEqual(directory / "2026-08-13.md", Path(saved["path"]))

            rejected = self.run_store(
                "append",
                "--directory",
                str(directory),
                "--date",
                "2026-08-13",
                "--time",
                "09:01:00",
                "--confirmed-save",
                input_text="<!-- recovery-entry-end -->",
                expected=2,
            )
            self.assertIn("reserved journal boundary", rejected["error"])

    def test_existing_filename_skips_first_save_warning_without_reading_other_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "journals"
            directory.mkdir()
            existing = directory / "2026-08-12.md"
            existing.write_text("not a journal entry", encoding="utf-8")
            existing.chmod(0)
            try:
                result = self.run_store(
                    "append",
                    "--directory",
                    str(directory),
                    "--date",
                    "2026-08-13",
                    "--time",
                    "09:01:00",
                    "--confirmed-save",
                    input_text="Next entry",
                )
            finally:
                existing.chmod(0o600)
            self.assertEqual("appended", result["action"])

    def test_invalid_date_shaped_filename_does_not_skip_warning(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "journals"
            directory.mkdir()
            (directory / "2026-99-99.md").write_text("decoy", encoding="utf-8")
            result = self.run_store(
                "append",
                "--directory",
                str(directory),
                "--date",
                "2026-08-13",
                "--time",
                "09:01:00",
                "--confirmed-save",
                input_text="First real entry",
                expected=2,
            )
            self.assertIn("plaintext warning", result["error"])

    def test_append_read_range_and_search(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "journals"
            base = ("--directory", str(directory), "--confirmed-save")
            self.run_store(
                "append", *base, "--plaintext-warning-shown", "--date", "2026-08-12", "--time", "08:00:00",
                input_text="Morning walk",
            )
            self.run_store(
                "append", *base, "--date", "2026-08-13", "--time", "09:00:00", input_text="Called Alex",
            )
            self.run_store(
                "append", *base, "--date", "2026-08-13", "--time", "10:00:00", input_text="Second walk",
            )

            read = self.run_store(
                "read", "--directory", str(directory), "--from-date", "2026-08-13", "--to-date", "2026-08-13"
            )
            self.assertEqual(["09:00:00", "10:00:00"], [entry["time"] for entry in read["entries"]])

            all_matches = self.run_store("search", "--directory", str(directory), "--query", "walk")
            self.assertEqual(2, len(all_matches["entries"]))
            ranged = self.run_store(
                "search", "--directory", str(directory), "--query", "walk",
                "--from-date", "2026-08-13", "--to-date", "2026-08-13",
            )
            self.assertEqual(["2026-08-13"], [entry["date"] for entry in ranged["entries"]])

    def test_edit_and_delete_are_guarded_and_atomic(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "journals"
            self.run_store(
                "append", "--directory", str(directory), "--date", "2026-08-13", "--time", "09:00:00",
                "--confirmed-save", "--plaintext-warning-shown", input_text="Original",
            )
            edit_args = (
                "edit", "--directory", str(directory), "--date", "2026-08-13", "--time", "09:00:00"
            )
            self.run_store(*edit_args, input_text="Changed", expected=2)
            edited = self.run_store(*edit_args, "--confirmed-edit", input_text="Changed")
            self.assertEqual("edited", edited["action"])
            self.assertFalse(any(path.name.startswith(".journal-") for path in directory.iterdir()))

            delete_args = (
                "delete", "--directory", str(directory), "--date", "2026-08-13", "--time", "09:00:00"
            )
            self.run_store(*delete_args, expected=2)
            deleted = self.run_store(*delete_args, "--confirmed-delete")
            self.assertEqual("deleted", deleted["action"])
            read = self.run_store(
                "read", "--directory", str(directory), "--from-date", "2026-08-13", "--to-date", "2026-08-13"
            )
            self.assertEqual([], read["entries"])
            self.assertFalse(any(path.name.startswith(".journal-") for path in directory.iterdir()))


if __name__ == "__main__":
    unittest.main()
