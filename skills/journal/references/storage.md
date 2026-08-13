# Journal storage contract

## Destinations

- POSIX: `<Documents>/recovery-journals/YYYY-MM-DD.md`
- Windows: `<My Documents>\Recovery Journal\YYYY-MM-DD.md`

The working-directory path determines the platform only. It does not determine where journals are stored. Ask when the working-directory path is ambiguous.

## File format

Files are unencrypted UTF-8 Markdown. Each entry has a local-time heading and internal Markdown comments that give edit and delete operations an exact boundary:

```markdown
# Recovery Journal: 2026-08-13

<!-- recovery-entry-start: 14:05:09 -->
## 14:05:09

Entry text.
<!-- recovery-entry-end -->
```

Normal saves append. Edits and deletions replace the daily file atomically without a backup. Duplicate timestamps are rejected rather than guessed.

## Privacy properties

- Directory and new file permissions are restricted where the operating system supports them.
- Plaintext files may still be synced, backed up, indexed, or visible to other people or apps.
- The filename-only first-save check does not inspect journal contents.
- Write commands require explicit authorization flags. The first save also requires acknowledgment that the plaintext warning was shown.
