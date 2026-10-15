import contextlib
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path

import habitstreak


class HabitStreakTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 10, 15)
        self.data = {"habits": []}

    def test_add_rejects_case_insensitive_duplicate(self):
        habitstreak.add_habit(self.data, "Reading", self.today)
        with self.assertRaisesRegex(habitstreak.HabitError, "already exists"):
            habitstreak.add_habit(self.data, " reading ", self.today)

    def test_add_rejects_blank_name(self):
        with self.assertRaisesRegex(habitstreak.HabitError, "cannot be blank"):
            habitstreak.add_habit(self.data, "   ", self.today)

    def test_list_and_remove_habits(self):
        habitstreak.add_habit(self.data, "Yoga", self.today)
        habitstreak.add_habit(self.data, "Reading", self.today)
        self.assertEqual(
            [habit["name"] for habit in habitstreak.list_habits(self.data)],
            ["Reading", "Yoga"],
        )
        removed = habitstreak.remove_habit(self.data, "yoga")
        self.assertEqual(removed["name"], "Yoga")
        self.assertEqual([habit["name"] for habit in self.data["habits"]], ["Reading"])

    def test_missing_file_and_json_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "habits.json"
            data = habitstreak.load_data(path)
            habitstreak.add_habit(data, "Reading", self.today)
            habitstreak.check_in(data, "Reading", self.today)
            habitstreak.save_data(path, data)
            self.assertEqual(habitstreak.load_data(path), data)

    def test_check_in_is_idempotent(self):
        habitstreak.add_habit(self.data, "Reading", self.today)
        habitstreak.check_in(self.data, "Reading", self.today)
        habitstreak.check_in(self.data, "reading", self.today)
        self.assertEqual(self.data["habits"][0]["completions"], ["2026-10-15"])

    def test_current_and_longest_streaks(self):
        cases = (
            (["2026-10-14", "2026-10-15"], (2, 2)),
            (["2026-10-14"], (1, 1)),
            (["2026-10-13"], (0, 1)),
            ([], (0, 0)),
            (["2026-10-10", "2026-10-11", "2026-10-13", "2026-10-14"], (2, 2)),
        )
        for completions, expected in cases:
            with self.subTest(completions=completions):
                self.assertEqual(
                    habitstreak.calculate_streaks(completions, self.today), expected
                )

    def test_malformed_json_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "habits.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaisesRegex(habitstreak.HabitError, "invalid JSON"):
                habitstreak.load_data(path)

    def test_cli_commands_persist_to_data_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "habits.json")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    habitstreak.main(
                        ["--data-file", path, "add", "Reading"], self.today
                    ),
                    0,
                )
                self.assertEqual(
                    habitstreak.main(
                        ["--data-file", path, "check-in", "Reading"], self.today
                    ),
                    0,
                )
                self.assertEqual(
                    habitstreak.main(["--data-file", path, "stats", "Reading"], self.today),
                    0,
                )
                self.assertEqual(
                    habitstreak.main(["--data-file", path, "remove", "Reading"], self.today),
                    0,
                )
            self.assertIn("Current streak: 1 day(s)", output.getvalue())
            self.assertEqual(habitstreak.load_data(path), {"habits": []})

    def test_cli_reports_unknown_habit_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            error_output = io.StringIO()
            with contextlib.redirect_stderr(error_output):
                result = habitstreak.main(
                    ["--data-file", str(Path(directory) / "habits.json"), "stats", "Missing"],
                    self.today,
                )
            self.assertEqual(result, 1)
            self.assertIn("Error: habit not found", error_output.getvalue())
            self.assertNotIn("Traceback", error_output.getvalue())


if __name__ == "__main__":
    unittest.main()