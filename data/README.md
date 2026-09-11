# Local research data

`data/` separates private source material from the records that SignalWeave
can safely use as reviewable research artefacts.

```text
data/
├── raw/                         # private and Git-ignored
│   └── <source_key>/
│       ├── transcripts/          # one transcript per source item
│       └── posts/                # one observed post per file
├── inbox/                       # private candidate event cards
├── private/                     # private identity maps and working notes
└── reviewed/                    # de-identified, human-approved records
    ├── events/
    └── threads/
```

Use a stable local `<source_key>` for every source. Raw files should retain
their original date or episode identifier so that a source locator can point
back to them without putting source wording or names in reviewed records.

`raw/`, `inbox/`, and `private/` are intentionally ignored by Git. Only put
material in `reviewed/` after human review and de-identification; run
`uv run signalweave public-check` before publishing changes.
