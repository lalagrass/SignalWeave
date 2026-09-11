# Adjacent open-source landscape (surveyed 2026-09-11)

Purpose: check whether SignalWeave's core loop — private source → candidate
event → human review → append-only thread → revisit — already exists as
open-source software, and record what is worth borrowing rather than building.

## Conclusion

No open-source project implements this loop end to end. The neighbours split
into four families, each of which owns one stage and ignores the others:

| Family | Owns | Missing for our case |
| --- | --- | --- |
| Structured-analytic (ACH) | hypothesis vs evidence matrix | no ingestion, no dated thread history, unmaintained |
| Prompt pipelines | transcript → structured claims | stateless; no review gate, no records |
| Agent memory / PKM | durable notes, local storage | free-form; no review gate, no invalidation or revisit contract |
| Thesis journals | thesis, review dates, risk checklists | asset-centric; no source ingestion, no candidate inbox |

The differentiator to keep is the **review gate plus the privacy boundary**:
machine-proposed candidates that cannot promote themselves, and tracked records
that never carry raw source text.

## Family 1 — structured analytic techniques

- `twschiller/open-synthesis` — Django platform for CIA-style Analysis of
  Competing Hypotheses; ~211 stars, **archived May 2026**. Closest conceptual
  relative: evidence scored against competing hypotheses by human analysts.
- `Burton/Analysis-of-Competing-Hypotheses` (PARC / competinghypotheses.org) —
  the original open-source ACH desktop tool; long dormant.
- `ApartsinProjects/EMR-ACH` — recent LLM + ACH evidence-matrix forecasting
  experiment. Research code, not a product.

Borrow: ACH's discipline of seeking *discriminating* evidence (evidence that
separates hypotheses), and of recording counter-evidence as a first-class field
rather than a note. Do not borrow the scoring matrix — it produces a verdict,
which the product boundary rejects.

## Family 2 — prompt pipelines over transcripts

- `danielmiessler/fabric` — ~43.9k stars, actively released. Patterns such as
  `extract_wisdom` and `analyze_claims` do transcript → structured output today.
  Stateless: output goes to stdout or a file; no records, no review, no history.

Borrow: pattern library shape for the future proposer. A pattern is a good
reference implementation of the `CandidateProposer` protocol in ADR-0003.

## Family 3 — agent memory and local-first PKM

- Basic Memory, mem0, Zep, Letta, cognee — durable memory for assistants;
  markdown or graph storage, MCP interfaces.
- Khoj, Reor, Logseq — local-first private note bases with AI search.

All optimise recall of what was said. None model an unresolved hypothesis with
an invalidation condition and a due date, and none gate writes behind a human
decision. They are a storage substrate, not the product.

## Family 4 — investment thesis journals

- `SergioYin/invest-thesis-ledger` (MIT, Python, 0 stars) — the closest field
  match: thesis records with dated sources, stale-source warnings, assumptions
  with confidence, risks, review history, snapshot `compare`, and an explicit
  no-recommendation boundary. Organised per asset, fed by hand; no ingestion
  lens, no candidate inbox, no source-privacy contract.
- Commercial thesis monitors (Helm Terminal, MyThesis, ThesisWatch and others,
  Aug 2026) are SaaS, asset-centric, and read public filings.

Borrow: stale-source warnings computed from record dates rather than wall-clock
time — deterministic and testable. Consider an equivalent for an overdue
`review_date`.

## Not the same problem

Evidence-synthesis and screening tools (ASReview, Covidence-likes) share the
inbox-and-decision shape but assume a large literature corpus and a one-off
review, not a small stream of recurring private sources with living threads.
