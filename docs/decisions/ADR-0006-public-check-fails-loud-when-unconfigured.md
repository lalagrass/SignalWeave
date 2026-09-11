# ADR-0006: `public-check` fails loudly when unconfigured, and flags private-zone locators

## Status

Accepted

## Context

`public-check`'s private-term scan reads `.signalweave/private_terms.txt` and
treats a missing file as "no terms" (`private_terms()` returns `[]`). That
made an unconfigured workspace indistinguishable from a workspace with
nothing left to protect: the command printed "Publication check passed" in
both cases. In practice, an unconfigured repository is the more likely and
more dangerous state — nothing has been reviewed for a term list that was
simply never set up.

This was not theoretical. The first-walkthrough-v0 commit landed a real
private source path inside tracked `docs/roadmap.md` (see that file's
"Follow-up fixes" note; the real path is deliberately not repeated here).
`public-check` "passed" on that tree because `.signalweave/private_terms.txt`
did not exist locally; had the source key been a configured term, the
existing scan would already have caught it. The leak was found by a human
planning review, not by the tool meant to catch it.

Separately, a source locator is identifying on its own even without a
configured term: naming a real subpath under `data/raw/`, `data/inbox/`, or
`data/private/` (a source key, a filename, a document date) leaks structure
about the private material regardless of whether that exact string was ever
added to a term list.

## Decision

`public-check` now calls `require_configuration()` before scanning. If
`.signalweave/private_terms.txt` is absent, it refuses to run and names the
missing file and the fix (create the file, or pass `--allow-unconfigured` for
a workspace that genuinely has no terms to configure). The file itself is
never committed — `.signalweave/private_terms.txt` was already git-ignored;
the setup step (copy `private_terms.example.txt`, then edit it) is documented
in `README.md`'s "Privacy and publishing" section instead of being satisfied
by shipping a real one.

`violations()` also flags any tracked file whose content names a
`data/raw/`, `data/inbox/`, or `data/private/` path more specific than the
bare zone or one of its fixed schema subfolders (`events/`, `reviews/`,
`threads/`, `worklog/`). This runs independently of the configured term list,
since a locator can be identifying even when no one thought to list it as a
term. `tests/` and `examples/` are exempt from this specific check, because
ADR-0001 already commits those directories to synthetic-only content, and a
test asserting the literal text of a blocked-path error message would
otherwise trip on its own fixture string.

## Consequences

- A freshly cloned or newly onboarded workspace cannot silently "pass"
  publication checks it never actually ran; first use forces a deliberate
  choice (configure it, or explicitly opt out).
- `--allow-unconfigured` keeps the check usable for a workspace with no
  private vocabulary yet, without weakening the default.
- The locator check catches a class of leak (a bare path reference) that no
  term list would catch unless someone had already thought to add that exact
  source key or filename as a term — the two checks are complementary, not
  redundant.
- The locator check's safe list is a fixed, small vocabulary
  (`events/`, `reviews/`, `threads/`, `worklog/`); a future storage zone
  addition must extend `SAFE_PRIVATE_LOCATOR_PATTERNS` in `public_check.py`
  or its bare-zone documentation will start failing the check.
