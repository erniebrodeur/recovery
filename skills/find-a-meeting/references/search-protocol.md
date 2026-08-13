# Meeting search protocol

## Interpret the request

- Resolve relative dates such as `tonight` to an explicit calendar date using the user's stated location and current date.
- Treat `public` and `open` as a request for a meeting anyone may attend.
- Treat `private` and `closed` as a request for a meeting limited to people with the relevant recovery concern.
- Preserve the directory's actual wording because programs define eligibility differently.
- Treat online as a location choice when no physical geography is needed. A timezone or usable time window is still required.

## Find candidates

1. Form queries from the requested approach, place or online format, date or weekday, and the words `official meetings` or `meeting finder`.
2. Prefer the program's own directory or the official regional provider responsible for that listing.
3. Open the candidate listing and verify details on the page itself. Search snippets and remembered schedules are discovery aids, not evidence.
4. Check recurrence against the requested calendar date. Reject a listing whose weekday, date, or active status does not fit.
5. For an online result, confirm where the user obtains access. For an in-person result, confirm the venue address or state that the official listing withholds it.
6. Check whether registration, membership, invitation, a password, or contact with the host is required.
7. Record the retrieval date. Record a page update date only when the source actually publishes one.

## Handle timezones

- Report an explicit timezone for every result.
- Prefer a timezone stated by the listing.
- Treat a directory's dynamically localized display time as unverified when its detected timezone is missing, stale, or marked `reset`. Use an explicit selected timezone or the listing's canonical calendar timestamp and timezone instead.
- For an in-person listing that gives a city but no timezone, infer the local timezone only from reliable geographic evidence and label it `timezone inferred from location`.
- For online listings, do not assume the viewer's timezone. Confirm whether the directory localizes times or names a timezone.
- When daylight-saving rules affect a future occurrence, verify the offset for that occurrence rather than reusing today's offset.
- Label every conversion, including both the source timezone and the timezone shown to the user.

## Return useful options

- Prefer two to five strong results over a long directory dump.
- Link to the individual listing when available, otherwise to the filtered official results page.
- Do not reproduce a facilitator's email address or phone number unless contacting the facilitator is required for legitimate access. Prefer the official contact control or listing page.
- Explain a material mismatch in one short phrase, such as `30 minutes later than requested`.
- If official sources conflict, report the conflict and do not present the meeting as verified.
- If a meeting is closed or private, report its eligibility and legitimate access step. Never provide a way around it.
