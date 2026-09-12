"""Model-backed pipeline steps: propose, story draft, basket draft.

Each step is provider-agnostic given any `ModelClient` (dependency injection
keeps this testable without a network call or a credential) and records its
own `Run` before returning, so every model call is individually storable and
later comparable (ADR-0009, `docs/specs/milestone-2-v0.md` DO-3/"Pipeline").

The concrete Anthropic wiring lives in `AnthropicModelClient` at the bottom —
the only place this module touches the `anthropic` package. `model_locality`
is always `"remote"` here: there is no local-model path yet, so a source
configured local-only must never reach this class (the caller's job, per
ADR-0009 — see `pipeline.py`).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
import json
import os
import re

from signalweave.extract import TranscriptSegment
from signalweave.runs import create_run, write_run


class ProposeError(RuntimeError):
    """Raised when a model call or its output cannot be used."""


class ModelClient(Protocol):
    """The one thing every provider adapter must do: complete a prompt."""

    def complete(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class ModelIdentity:
    """Which model produced a call, and how it must be recorded (ADR-0009)."""

    provider: str
    model_id: str
    model_locality: str


def load_method(name: str, methods_directory: Path) -> str:
    """Read a tracked, versioned prompt file. Contains no source text."""
    path = methods_directory / f"{name}.md"
    return path.read_text(encoding="utf-8")


def render_method(template: str, **values: str) -> str:
    """Fill a method template's named placeholders with a plain substring
    replace — not `str.format`, because the templates themselves contain
    literal `{...}` JSON examples that `str.format` would misread as fields.
    """
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{key}}}", value)
    return rendered


def drafted_by_for(model_id: str) -> str:
    """A schema-safe identifier for `drafted_by` from an arbitrary model id."""
    sanitized = re.sub(r"[^a-z0-9_]", "_", model_id.lower())
    return f"model_{sanitized}"


def _call_and_record(
    client: ModelClient,
    identity: ModelIdentity,
    *,
    runs_directory: Path,
    method_version: str,
    input_id: str,
    prompt: str,
) -> tuple[str, str]:
    """Call the model, record the run, and return (output, run_id)."""
    output = client.complete(prompt)
    run = create_run(
        provider=identity.provider,
        model_id=identity.model_id,
        model_locality=identity.model_locality,
        method_version=method_version,
        input_id=input_id,
        output=output,
    )
    write_run(run, runs_directory)
    return output, run.run_id


def _parse_json(output: str) -> Any:
    text = output.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[: -3]
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ProposeError(f"model output was not valid JSON: {error}") from error


class ModelBackedCandidateProposer:
    """A real `CandidateProposer` (ADR-0003 protocol) backed by a model call.

    One call per segment. Every proposal this returns carries `drafted_by`
    and `run_id`; `extract_candidates` (extract.py) still overwrites `source`,
    `source_locator`, and `review_status`, and still enforces the span-exists
    check — this class supplies the raw material, not the gate.
    """

    def __init__(
        self,
        client: ModelClient,
        identity: ModelIdentity,
        *,
        method_template: str,
        event_date: str,
        runs_directory: Path,
        method_version: str = "propose_v1",
    ) -> None:
        self._client = client
        self._identity = identity
        self._method_template = method_template
        self._event_date = event_date
        self._runs_directory = runs_directory
        self._method_version = method_version

    def propose(self, segment: TranscriptSegment) -> Iterable[Mapping[str, Any]]:
        prompt = render_method(self._method_template, segment_text=segment.text)
        output, run_id = _call_and_record(
            self._client,
            self._identity,
            runs_directory=self._runs_directory,
            method_version=self._method_version,
            input_id=segment.source_locator,
            prompt=prompt,
        )
        proposals = _parse_json(output)
        if not isinstance(proposals, list):
            raise ProposeError("propose_v1 output must be a JSON array")

        document_id = segment.source_locator.split("#", 1)[0]
        drafted_by = drafted_by_for(self._identity.model_id)
        results = []
        for index, item in enumerate(proposals, start=1):
            if not isinstance(item, dict):
                raise ProposeError("each proposal must be a JSON object")
            results.append(
                {
                    "event_id": f"evt_{document_id}_{segment.position:03d}_{index:02d}",
                    "date": self._event_date,
                    "kind": item.get("kind"),
                    "summary": item.get("summary"),
                    "uncertainty": item.get("uncertainty"),
                    "cited_span": item.get("cited_span"),
                    "claims": item.get("claims", []),
                    "mechanisms": item.get("mechanisms", []),
                    "counterarguments": item.get("counterarguments", []),
                    "drafted_by": drafted_by,
                    "run_id": run_id,
                }
            )
        return results


@dataclass(frozen=True)
class DraftedStory:
    """The output of the story-draft step, before it becomes a `ResearchThread`."""

    mechanism: str
    open_question: str
    invalidation_conditions: list[str]
    groups: list[str]
    market_sentiment: str
    drafted_by: str
    run_id: str


class ModelBackedStoryProposer:
    """One model call per pipeline run: events in, a story draft out."""

    def __init__(
        self,
        client: ModelClient,
        identity: ModelIdentity,
        *,
        method_template: str,
        runs_directory: Path,
        method_version: str = "story_v1",
    ) -> None:
        self._client = client
        self._identity = identity
        self._method_template = method_template
        self._runs_directory = runs_directory
        self._method_version = method_version

    def propose(self, event_summaries: Sequence[str], *, input_id: str) -> DraftedStory:
        joined = "\n".join(f"- {summary}" for summary in event_summaries)
        prompt = render_method(self._method_template, observation_summaries=joined)
        output, run_id = _call_and_record(
            self._client,
            self._identity,
            runs_directory=self._runs_directory,
            method_version=self._method_version,
            input_id=input_id,
            prompt=prompt,
        )
        story = _parse_json(output)
        if not isinstance(story, dict):
            raise ProposeError("story_v1 output must be a JSON object")
        return DraftedStory(
            mechanism=story.get("mechanism", ""),
            open_question=story.get("open_question", ""),
            invalidation_conditions=list(story.get("invalidation_conditions", [])),
            groups=list(story.get("groups", [])),
            market_sentiment=story.get("market_sentiment", ""),
            drafted_by=drafted_by_for(self._identity.model_id),
            run_id=run_id,
        )


class ModelBackedBasketProposer:
    """One model call per pipeline run: a story in, an instrument list out."""

    def __init__(
        self,
        client: ModelClient,
        identity: ModelIdentity,
        *,
        method_template: str,
        runs_directory: Path,
        method_version: str = "basket_v1",
    ) -> None:
        self._client = client
        self._identity = identity
        self._method_template = method_template
        self._runs_directory = runs_directory
        self._method_version = method_version

    def propose(self, story: DraftedStory, *, input_id: str) -> tuple[list[str], str]:
        """Return (instruments, run_id)."""
        prompt = render_method(
            self._method_template,
            mechanism=story.mechanism,
            groups=", ".join(story.groups),
            market_sentiment=story.market_sentiment,
        )
        output, run_id = _call_and_record(
            self._client,
            self._identity,
            runs_directory=self._runs_directory,
            method_version=self._method_version,
            input_id=input_id,
            prompt=prompt,
        )
        parsed = _parse_json(output)
        if not isinstance(parsed, dict) or "instruments" not in parsed:
            raise ProposeError("basket_v1 output must be a JSON object with an instruments field")
        instruments = parsed["instruments"]
        if not isinstance(instruments, list):
            raise ProposeError("basket_v1 instruments must be a JSON array")
        return list(instruments), run_id


class AnthropicModelClient:
    """The only place this project depends on the `anthropic` package.

    Reads its API key from the `ANTHROPIC_API_KEY` environment variable via
    the SDK's own default — never accepted as a CLI argument, never
    committed. See ADR-0009: every call this makes sends segment or story
    text to a remote provider.
    """

    def __init__(self, *, model_id: str, max_tokens: int = 2048) -> None:
        import anthropic  # deferred: only imported when this class is used

        if not os.environ.get("ANTHROPIC_API_KEY"):
            # Checked explicitly rather than left to the SDK: its own missing-key
            # error surfaces as a bare TypeError several frames deep, not
            # something callers can catch cleanly alongside our own errors.
            raise ProposeError(
                "ANTHROPIC_API_KEY is not set in the environment; export it before "
                "running the pipeline against a remote provider (ADR-0009)"
            )
        self._anthropic = anthropic
        try:
            self._client = anthropic.Anthropic()
        except anthropic.AnthropicError as error:
            raise ProposeError(f"could not set up the Anthropic client: {error}") from error
        self._model_id = model_id
        self._max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        try:
            response = self._client.messages.create(
                model=self._model_id,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except self._anthropic.AnthropicError as error:
            raise ProposeError(f"Anthropic API call failed: {error}") from error
        return "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
