### Fixed

**Secret scanners: empty-user URL credentials and whitespace parity** (2026-10-03)

- `secretscan.go`, `openrig_scrub.py`: the URL-credentials user part may be empty, so the standard Redis form `redis://:password@host` is detected and redacted (found by the reviewer in 9468eb28). An empty password (`ftp://user:@host`) is deliberately not flagged: nothing to leak.
- `openrig_scrub.py`: Go `\s` is ASCII-only `[\t\n\f\r ]` while Python `\s` is Unicode, so `http://u:pass<NBSP>word@db` was redacted by the server scan but not by the bridge scrubber. The bearer, URL and password/token patterns now spell the Go class out (`_WS`/`_NOT_WS`); `re.ASCII` was not used because it also treats the vertical tab as whitespace, which Go does not.
- Known gap (fixture case `known-gap-url-slash-in-password`): a raw `/` inside a URL password (`postgres://user:pa/ssword99@db/app`) is not detected, since `/` ends the userinfo; widening it would flag ordinary URLs.
