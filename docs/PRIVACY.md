# Privacy contract

SignalWeave is designed for private-source research. A public repository must
contain only software, schemas, synthetic examples, and de-identified summaries.

## Never commit

- original transcripts, posts, screenshots, audio, captions, or exports;
- source/show/account/person names and handles, unless explicitly approved;
- long or distinctive quotations;
- local identity maps, credentials, or private URLs;
- generated cards before they have been reviewed and de-identified.

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

## Release procedure

1. Run `uv run signalweave public-check`.
2. Review all staged changes, including generated Markdown and YAML.
3. Confirm no raw content, unique source wording, names, handles, URLs, or
   identity-map files remain.
4. Treat a clean scan as necessary but insufficient; approve publication by eye.

