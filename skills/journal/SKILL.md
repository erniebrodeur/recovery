---
name: journal
description: Draft, explicitly save, read, search, edit, or delete Recovery journal entries stored as plaintext daily Markdown files. Use when an adult asks to journal, save a journal entry, retrieve entries for named dates, search saved entries, revise a specific time-stamped entry, or delete one.
---

# Recovery Journal

Keep persistence opt-in and operations narrowly scoped. Never interpret journal text psychologically.

## Required references

Read these files completely before acting:

- `../recovery-help/references/privacy.md`
- `../recovery-help/references/safety.md`
- `references/storage.md`

When this skill supplies the first Recovery response in a conversation, show the complete session warning from `../recovery-help/references/privacy.md` verbatim. This is separate from the first-save plaintext warning. Do not repeat the session warning later in the same conversation.

## Draft

- Draft or organize only the text the user provides.
- Keep the draft in the conversation unless the user explicitly asks to save it.
- Do not treat a request to draft, rewrite, summarize, or format as permission to save.
- Produce factual summaries without diagnosis, counseling, or inferred psychological meaning.

## Resolve storage

Use the current working-directory path for best-effort platform detection:

- Treat a drive-style path such as `C:\Users\name\project` as Windows.
- Treat a path beginning with `/` as POSIX.
- Ask which platform to use when the path is neither form. Do not write while it is ambiguous.

Use `scripts/journal_store.py resolve-directory --cwd <path>` when useful. On POSIX, store entries under the user's Documents directory in `recovery-journals`. On Windows, use the user's My Documents directory in `Recovery Journal`. If the operating system exposes a canonical Documents location, prefer it over assuming a literal folder name.

## Save

Treat a direct request such as "save this" as permission for that entry only.

1. Resolve the destination without creating it.
2. Run `has-entries`. It checks date-shaped filenames only and must not read entry contents.
3. If no date-shaped entry exists, warn: `This journal is plaintext. Your Documents folder may be synced, backed up, or visible to other people or apps.`
4. Identify the exact entry text and destination path before writing.
5. Use the user's local date as `YYYY-MM-DD.md` and local time as an `HH:MM:SS` heading.
6. Pass text to `append` through standard input or a restrictive temporary file, never as a command argument. Include `--confirmed-save`; on the first save also include `--plaintext-warning-shown`.
7. Report the exact path returned by the utility immediately after success.

Normal saves append a new entry and never discard existing entries.

## Read and search

- Read only a single date or inclusive date range the user explicitly names.
- Require an explicit request to search all entries. Never scan or summarize journals automatically.
- Use `read` with both date bounds, including the same bound twice for one day.
- Use `search` only for the query and optional date bounds the user requested.
- Return only responsive entries and state when no entries match.

## Edit

- Require an explicit edit request and identify the date and time-stamped entry.
- Read only the named date when needed to resolve the target.
- Ask when the target is ambiguous.
- Show the replacement text and exact file path before writing.
- Use `edit` with `--confirmed-edit`. It changes one entry atomically and creates no backup.
- Report the date, time, and exact path changed.

## Delete

- Require an explicit deletion request and identify one date and time-stamped entry.
- Ask when the target is ambiguous.
- Show the target date, time, and exact path, then obtain confirmation before deletion.
- Only after confirmation, use `delete` with `--confirmed-delete`.
- Report the date, time, and exact path changed. Do not imply the chat copy was deleted.

## Utility contract

Run `python3 scripts/journal_store.py --help` for the exact interface. The utility emits JSON, rejects unauthorized writes, validates dates and times, uses atomic replacement for mutations, and does not create hidden backups.
