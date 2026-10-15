"""A small JSON-backed daily habit tracker."""

import argparse
import json
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path


class HabitError(Exception):
    """An expected validation or lookup error for a habit operation."""


def normalize_name(name):
    normalized = name.strip()
    if not normalized:
        raise HabitError("habit name cannot be blank")
    return normalized


def find_habit(data, name):
    target = normalize_name(name).casefold()
    for habit in data["habits"]:
        if habit["name"].casefold() == target:
            return habit
    raise HabitError(f"habit not found: {name}")


def _parse_date(value, field):
    if not isinstance(value, str):
        raise HabitError(f"invalid stored data: {field} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise HabitError(f"invalid stored data: {field} must be an ISO date") from error
    if parsed.isoformat() != value:
        raise HabitError(f"invalid stored data: {field} must be an ISO date")
    return parsed


def validate_data(data):
    if not isinstance(data, dict) or not isinstance(data.get("habits"), list):
        raise HabitError("invalid stored data: expected an object with a habits list")

    names = set()
    for habit in data["habits"]:
        if not isinstance(habit, dict):
            raise HabitError("invalid stored data: each habit must be an object")
        name = habit.get("name")
        if not isinstance(name, str) or not name.strip():
            raise HabitError("invalid stored data: each habit needs a non-blank name")
        normalized_name = name.casefold()
        if normalized_name in names:
            raise HabitError("invalid stored data: habit names must be unique")
        names.add(normalized_name)

        _parse_date(habit.get("created_on"), "created_on")
        completions = habit.get("completions")
        if not isinstance(completions, list):
            raise HabitError("invalid stored data: completions must be a list")
        parsed_completions = [_parse_date(item, "completion") for item in completions]
        if parsed_completions != sorted(set(parsed_completions)):
            raise HabitError("invalid stored data: completions must be unique and sorted")


def load_data(path):
    path = Path(path).expanduser()
    if not path.exists():
        return {"habits": []}
    try:
        with path.open("r", encoding="utf-8") as data_file:
            data = json.load(data_file)
    except json.JSONDecodeError as error:
        raise HabitError(f"invalid JSON in {path}: {error.msg}") from error
    validate_data(data)
    return data


def save_data(path, data):
    path = Path(path).expanduser()
    validate_data(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as data_file:
            json.dump(data, data_file, indent=2)
            data_file.write("\n")
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def add_habit(data, name, today=None):
    name = normalize_name(name)
    if any(habit["name"].casefold() == name.casefold() for habit in data["habits"]):
        raise HabitError(f"habit already exists: {name}")
    created_on = (today or date.today()).isoformat()
    habit = {"name": name, "created_on": created_on, "completions": []}
    data["habits"].append(habit)
    return habit


def list_habits(data):
    return sorted(data["habits"], key=lambda habit: habit["name"].casefold())


def check_in(data, name, today=None):
    habit = find_habit(data, name)
    completion = (today or date.today()).isoformat()
    if completion not in habit["completions"]:
        habit["completions"].append(completion)
        habit["completions"].sort()
    return habit


def remove_habit(data, name):
    habit = find_habit(data, name)
    data["habits"].remove(habit)
    return habit


def calculate_streaks(completions, today=None):
    today = today or date.today()
    completion_dates = {_parse_date(item, "completion") for item in completions}

    longest = 0
    current_run = 0
    previous = None
    for completed_on in sorted(completion_dates):
        if previous is not None and completed_on == previous + timedelta(days=1):
            current_run += 1
        else:
            current_run = 1
        longest = max(longest, current_run)
        previous = completed_on

    streak_end = today if today in completion_dates else today - timedelta(days=1)
    current = 0
    while streak_end in completion_dates:
        current += 1
        streak_end -= timedelta(days=1)
    return current, longest


def build_parser():
    parser = argparse.ArgumentParser(prog="habitstreak")
    parser.add_argument(
        "--data-file",
        type=Path,
        default=Path.home() / ".habitstreak" / "habits.json",
        help="JSON data file (default: ~/.habitstreak/habits.json)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add_parser = commands.add_parser("add", help="add a habit")
    add_parser.add_argument("name", help="habit name")

    commands.add_parser("list", help="list habits")

    check_in_parser = commands.add_parser("check-in", help="record today's completion")
    check_in_parser.add_argument("name", help="habit name")

    stats_parser = commands.add_parser("stats", help="show streaks for a habit")
    stats_parser.add_argument("name", help="habit name")

    remove_parser = commands.add_parser("remove", help="remove a habit and its history")
    remove_parser.add_argument("name", help="habit name")
    return parser


def main(argv=None, today=None):
    args = build_parser().parse_args(argv)
    try:
        data = load_data(args.data_file)
        if args.command == "add":
            habit = add_habit(data, args.name, today)
            save_data(args.data_file, data)
            print(f"Added habit: {habit['name']}")
        elif args.command == "list":
            habits = list_habits(data)
            if not habits:
                print("No habits yet.")
            else:
                for habit in habits:
                    print(f"- {habit['name']}")
        elif args.command == "check-in":
            habit = check_in(data, args.name, today)
            save_data(args.data_file, data)
            print(f"Checked in: {habit['name']} ({(today or date.today()).isoformat()})")
        elif args.command == "stats":
            habit = find_habit(data, args.name)
            current, longest = calculate_streaks(habit["completions"], today)
            print(f"Stats for {habit['name']}:")
            print(f"  Current streak: {current} day(s)")
            print(f"  Longest streak: {longest} day(s)")
        elif args.command == "remove":
            habit = remove_habit(data, args.name)
            save_data(args.data_file, data)
            print(f"Removed habit: {habit['name']}")
    except (HabitError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())