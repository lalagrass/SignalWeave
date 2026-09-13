# Privacy contract

SignalWeave is designed for private-source research. A public repository must
contain only software, schemas, synthetic examples, and de-identified summaries.

## Local analysis is allowed

Agents and local tools may open, read, parse, hash, compare, and transform source
material in the authorized workspace when required for research, provenance, or
content-equivalence checks. Privacy is not a reason to defer a check to the user
when it can be performed safely on local files.

Keep source material and source-specific intermediate output in the ignored
private zones. Avoid printing raw passages when a targeted inspection, count, or
hash is sufficient. Any model-provider boundary crossing follows ADR-0009. The
restriction below applies to publication and Git, not to local analysis.

## Never commit

- original transcripts, posts, screenshots, audio, captions, or exports;
- source/show/account/person names and handles, unless explicitly approved;
- long or distinctive quotations;
- local identity maps, credentials, or private URLs;
- generated records that contain source text, identifying details, or unsafe
  locators. `review_status: unreviewed` alone does not make a de-identified
  record unsafe to track.

## Safe tracked record

```yaml
event_id: evt_2026_001
source: source_a
source_locator: doc_2026_001#segment_12
date: 2026-09-11
summary: A supplier constraint may shift bargaining power upstream.
```

The locator resolves only through an untracked local identity map. A summary is
written in new language; it is not a paraphrase-by-substitution of the source.
Machine-authored records may retain `review_status: unreviewed`; privacy is a
content and publication boundary, not a human-approval gate.

## Release procedure

1. Run `uv run signalweave public-check`.
2. Review all staged changes, including generated Markdown and YAML.
3. Confirm no raw content, unique source wording, names, handles, URLs, or
   identity-map files remain.
4. Treat a clean scan as necessary but insufficient; approve publication by eye.
