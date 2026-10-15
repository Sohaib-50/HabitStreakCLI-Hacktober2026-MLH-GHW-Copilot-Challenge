# HabitStreakCLI

A minimal command-line habit tracker for the MLH Global Hack Week Hacktoberfest challenge. It uses Python's standard library and stores data as JSON. Built for the [Use GitHub Copilot to Build a Simple Application challenge](https://www.mlh.com/challenges/01a11b46-2f5c-3ba2-3dac-73e6f58fd53e/) during MLH Global Hack Week Hacktober 2026.

Built and tested end to end with GitHub Copilot in Codespace, using following features:
1. `/init` to initialize the agent setup.
2. Plan mode to plan and scope the application.
3. Agent mode to implement the application and tests.
4. Copilot's Generate Commit Message feature.

## Requirements

- Python 3.7 or newer
- No third-party packages

## Usage

Add habits, quoting names that contain spaces:

```sh
python habitstreak.py add "Read 10 pages"
python habitstreak.py add Exercise
```

Check in once per day, list habits, and view streaks:

```sh
python habitstreak.py check-in "Read 10 pages"
python habitstreak.py list
python habitstreak.py stats "Read 10 pages"
```

Remove a habit and its check-in history:

```sh
python habitstreak.py remove Exercise
```

Habit names are case-insensitively unique. Repeating a check-in on the same day does not add another completion. A current streak includes consecutive check-ins through today, or through yesterday if today is not checked in yet; a missed day resets it. The longest streak is the longest run of consecutive completed days.

## Data

By default, data is saved to `~/.habitstreak/habits.json`. Choose another JSON file by passing `--data-file PATH` before the command:

```sh
python habitstreak.py --data-file ./habits.json add "Read 10 pages"
```

## Tests

Run the tests with Python's built-in test runner:

```sh
python -m unittest -v
```
