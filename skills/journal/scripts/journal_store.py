#!/usr/bin/env python3
"""Deterministic plaintext storage for the Recovery journal skill."""

from __future__ import annotations

import argparse
import json
import ntpath
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from datetime import date


DATE_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$")
ENTRY_RE = re.compile(
    r"^<!-- recovery-entry-start: (?P<time>(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d) -->\n"
    r"## (?P=time)\n\n"
    r"(?P<content>.*?)\n"
    r"<!-- recovery-entry-end -->\n?",
    re.MULTILINE | re.DOTALL,
)


class JournalError(Exception):
    pass


def validate_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise JournalError(f"invalid date: {value}") from exc
    if parsed.isoformat() != value:
        raise JournalError(f"date must use YYYY-MM-DD: {value}")
    return value


def validate_time(value: str) -> str:
    if not TIME_RE.fullmatch(value):
        raise JournalError(f"time must use HH:MM:SS: {value}")
    return value


def detect_platform(cwd: str) -> str:
    if re.match(r"^[A-Za-z]:[\\/]", cwd):
        return "windows"
    if cwd.startswith("/"):
        return "posix"
    return "ambiguous"


def resolve_directory(cwd: str, home: str | None = None) -> str:
    platform = detect_platform(cwd)
    if platform == "ambiguous":
        raise JournalError("working-directory path is ambiguous; ask the user which platform to use")
    if platform == "windows":
        if home is not None:
            documents = ntpath.join(home, "Documents")
        elif os.name == "nt":
            try:
                import winreg

                key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    documents = os.path.expandvars(winreg.QueryValueEx(key, "Personal")[0])
            except (OSError, ImportError):
                documents = ntpath.join(str(Path.home()), "Documents")
        else:
            documents = ntpath.join(str(Path.home()), "Documents")
        return ntpath.join(documents, "Recovery Journal")
    resolved_home = home or str(Path.home())
    return str(Path(resolved_home) / "Documents" / "recovery-journals")


def iter_date_files(directory: Path, start: str | None = None, end: str | None = None):
    if not directory.exists():
        return
    for candidate in sorted(directory.iterdir(), key=lambda item: item.name):
        match = DATE_FILE_RE.fullmatch(candidate.name)
        if not match or not candidate.is_file():
            continue
        day = match.group(1)
        try:
            validate_date(day)
        except JournalError:
            continue
        if start is not None and day < start:
            continue
        if end is not None and day > end:
            continue
        yield day, candidate


def has_entries(directory: Path) -> bool:
    return next(iter_date_files(directory), None) is not None


def read_content(source: str) -> str:
    if source == "-":
        content = sys.stdin.read()
    else:
        content = Path(source).read_text(encoding="utf-8")
    content = content.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    if not content.strip():
        raise JournalError("entry content cannot be empty")
    return content


def render_entry(entry_time: str, content: str) -> str:
    return (
        f"<!-- recovery-entry-start: {entry_time} -->\n"
        f"## {entry_time}\n\n"
        f"{content}\n"
        "<!-- recovery-entry-end -->\n"
    )


def validate_content(content: str) -> str:
    if "<!-- recovery-entry-start:" in content or "<!-- recovery-entry-end -->" in content:
        raise JournalError("entry content contains a reserved journal boundary marker")
    return content


def parse_entries(text: str) -> list[dict[str, str]]:
    return [
        {"time": match.group("time"), "content": match.group("content")}
        for match in ENTRY_RE.finditer(text)
    ]


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    existing_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, temporary_name = tempfile.mkstemp(prefix=".journal-", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(fd, existing_mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise


def append_entry(args: argparse.Namespace) -> dict[str, str]:
    if not args.confirmed_save:
        raise JournalError("save rejected: explicit save authorization is required")
    directory = Path(args.directory)
    first_save = not has_entries(directory)
    if first_save and not args.plaintext_warning_shown:
        raise JournalError("first save rejected: show the plaintext warning before writing")
    day = validate_date(args.date)
    entry_time = validate_time(args.time)
    content = validate_content(read_content(args.content_file))
    path = directory / f"{day}.md"
    if path.exists():
        current = path.read_text(encoding="utf-8")
    else:
        current = f"# Recovery Journal: {day}\n\n"
    if any(entry["time"] == entry_time for entry in parse_entries(current)):
        raise JournalError(f"an entry already exists at {entry_time}; choose the exact entry instead of guessing")
    if current and not current.endswith("\n"):
        current += "\n"
    atomic_write(path, current + render_entry(entry_time, content))
    return {"action": "appended", "date": day, "time": entry_time, "path": str(path)}


def read_entries(directory: Path, start: str, end: str) -> list[dict[str, str]]:
    validate_date(start)
    validate_date(end)
    if start > end:
        raise JournalError("from-date must not be after to-date")
    results: list[dict[str, str]] = []
    for day, path in iter_date_files(directory, start, end):
        for entry in parse_entries(path.read_text(encoding="utf-8")):
            results.append({"date": day, **entry, "path": str(path)})
    return results


def search_entries(args: argparse.Namespace) -> dict[str, object]:
    if (args.from_date is None) != (args.to_date is None):
        raise JournalError("provide both --from-date and --to-date, or neither")
    start = validate_date(args.from_date) if args.from_date else None
    end = validate_date(args.to_date) if args.to_date else None
    if start and end and start > end:
        raise JournalError("from-date must not be after to-date")
    query = args.query.casefold()
    if not query:
        raise JournalError("search query cannot be empty")
    matches: list[dict[str, str]] = []
    for day, path in iter_date_files(Path(args.directory), start, end):
        for entry in parse_entries(path.read_text(encoding="utf-8")):
            if query in entry["content"].casefold():
                matches.append({"date": day, **entry, "path": str(path)})
    return {"query": args.query, "entries": matches}


def replace_one(path: Path, entry_time: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    matches = [match for match in ENTRY_RE.finditer(text) if match.group("time") == entry_time]
    if not matches:
        raise JournalError(f"no entry exists at {entry_time}")
    if len(matches) > 1:
        raise JournalError(f"multiple entries exist at {entry_time}; target is ambiguous")
    match = matches[0]
    atomic_write(path, text[: match.start()] + replacement + text[match.end() :])


def edit_entry(args: argparse.Namespace) -> dict[str, str]:
    if not args.confirmed_edit:
        raise JournalError("edit rejected: explicit edit authorization is required")
    day = validate_date(args.date)
    entry_time = validate_time(args.time)
    content = validate_content(read_content(args.content_file))
    path = Path(args.directory) / f"{day}.md"
    if not path.is_file():
        raise JournalError(f"journal file does not exist: {path}")
    replace_one(path, entry_time, render_entry(entry_time, content))
    return {"action": "edited", "date": day, "time": entry_time, "path": str(path)}


def delete_entry(args: argparse.Namespace) -> dict[str, str]:
    if not args.confirmed_delete:
        raise JournalError("delete rejected: confirmation is required")
    day = validate_date(args.date)
    entry_time = validate_time(args.time)
    path = Path(args.directory) / f"{day}.md"
    if not path.is_file():
        raise JournalError(f"journal file does not exist: {path}")
    replace_one(path, entry_time, "")
    return {"action": "deleted", "date": day, "time": entry_time, "path": str(path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    detect = commands.add_parser("detect-platform")
    detect.add_argument("--cwd", required=True)

    resolve = commands.add_parser("resolve-directory")
    resolve.add_argument("--cwd", required=True)
    resolve.add_argument("--home")

    existing = commands.add_parser("has-entries")
    existing.add_argument("--directory", required=True)

    append = commands.add_parser("append")
    append.add_argument("--directory", required=True)
    append.add_argument("--date", required=True)
    append.add_argument("--time", required=True)
    append.add_argument("--content-file", default="-")
    append.add_argument("--confirmed-save", action="store_true")
    append.add_argument("--plaintext-warning-shown", action="store_true")

    read = commands.add_parser("read")
    read.add_argument("--directory", required=True)
    read.add_argument("--from-date", required=True)
    read.add_argument("--to-date", required=True)

    search = commands.add_parser("search")
    search.add_argument("--directory", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--from-date")
    search.add_argument("--to-date")

    edit = commands.add_parser("edit")
    edit.add_argument("--directory", required=True)
    edit.add_argument("--date", required=True)
    edit.add_argument("--time", required=True)
    edit.add_argument("--content-file", default="-")
    edit.add_argument("--confirmed-edit", action="store_true")

    delete = commands.add_parser("delete")
    delete.add_argument("--directory", required=True)
    delete.add_argument("--date", required=True)
    delete.add_argument("--time", required=True)
    delete.add_argument("--confirmed-delete", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "detect-platform":
            result: object = {"platform": detect_platform(args.cwd)}
        elif args.command == "resolve-directory":
            result = {"platform": detect_platform(args.cwd), "directory": resolve_directory(args.cwd, args.home)}
        elif args.command == "has-entries":
            result = {"has_entries": has_entries(Path(args.directory))}
        elif args.command == "append":
            result = append_entry(args)
        elif args.command == "read":
            result = {
                "from_date": args.from_date,
                "to_date": args.to_date,
                "entries": read_entries(Path(args.directory), args.from_date, args.to_date),
            }
        elif args.command == "search":
            result = search_entries(args)
        elif args.command == "edit":
            result = edit_entry(args)
        elif args.command == "delete":
            result = delete_entry(args)
        else:
            raise JournalError(f"unsupported command: {args.command}")
    except (JournalError, OSError, UnicodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
