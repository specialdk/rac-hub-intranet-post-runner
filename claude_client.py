"""Anthropic API calls for the three Claude-driven steps in the workflow.

Three structured-output calls, each with its own system prompt assembled
from the reference markdown files at module load:

    clean_text(...)        → text-cleaning-rules.md + rac-voice-guide.md
    generate_title(...)    → example-titles.md + rac-voice-guide.md
    generate_highlight(...)→ example-highlights.md + rac-voice-guide.md

Each system prompt is large (~10–20 KB each) and stable — exactly the shape
prompt caching is built for. We cache via `cache_control: ephemeral` on the
last system block. Inside a single run that processes 1–5 submissions, this
saves ~90% on input cost from the second submission's call onward.

Model: claude-opus-4-7. Editorial nuance matters here — we're enforcing rules
about Yolŋu words, Aboriginal English, and reported speech. Adaptive thinking
auto-decides depth per submission; output_config.effort defaults to high.

Output format: structured outputs via `messages.parse()` with Pydantic
models. Guarantees the cleaned/title/highlight fields plus the metadata
the AdminNote composer needs (filler count, swear count, etc.).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import anthropic
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Reference content — loaded once at module import
# ---------------------------------------------------------------------------

_REFERENCE_DIR = Path(__file__).parent / "reference"


def _load_ref(name: str) -> str:
    path = _REFERENCE_DIR / name
    return path.read_text(encoding="utf-8")


_TEXT_CLEANING_RULES = _load_ref("text-cleaning-rules.md")
_RAC_VOICE_GUIDE = _load_ref("rac-voice-guide.md")
_EXAMPLE_TITLES = _load_ref("example-titles.md")
_EXAMPLE_HIGHLIGHTS = _load_ref("example-highlights.md")


# ---------------------------------------------------------------------------
# Pydantic schemas — structured outputs
# ---------------------------------------------------------------------------

class CleanedText(BaseModel):
    """Result of the cleaning pass.

    The integer counters drive the AdminNote composition. `verbatim` is a
    convenience flag — true when no edits were made — so the AdminNote can
    say "Submitter's text used verbatim." rather than reciting four zeros.
    """

    cleaned_text: str = Field(
        description="The cleaned text. Pass-through verbatim if no edits were warranted."
    )
    verbatim: bool = Field(
        description="True if the submitter's text was used unchanged."
    )
    fillers_removed: int = Field(
        ge=0, description="Count of filler words removed (um, uh, like-as-filler, etc.)."
    )
    swears_removed: int = Field(
        ge=0, description="Count of swears removed cleanly (not in reported speech)."
    )
    stutters_fixed: int = Field(
        ge=0, description="Count of stutters or immediate self-corrections cleaned up."
    )
    paragraph_breaks_added: int = Field(
        ge=0, description="Count of paragraph breaks added for readability."
    )
    has_enumerated_list: bool = Field(
        description="True if the body contains an enumerated list that could be bulleted on review."
    )


class GeneratedTitle(BaseModel):
    title: str = Field(
        description=(
            "A 2–6 word sentence-case title generated from the cleaned text. "
            "No emoji, no clickbait. Leads with the most concrete element."
        )
    )


class GeneratedHighlight(BaseModel):
    highlight: str = Field(
        description=(
            "A short hook-style highlight, typically 5–15 words (up to 30 for "
            "multi-event recaps). Warm, specific, matches the feeling of the story. "
            "Optional single trailing emoji if it adds genuine meaning."
        )
    )


# ---------------------------------------------------------------------------
# Anthropic client
# ---------------------------------------------------------------------------

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var
    return _client


def _model() -> str:
    return os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")


def _max_tokens() -> int:
    return int(os.environ.get("CLAUDE_MAX_TOKENS", "4096"))


# ---------------------------------------------------------------------------
# System prompt builders
# ---------------------------------------------------------------------------
#
# Each system prompt is a list of two text blocks:
#   1. Identity + task instructions (small, framing)
#   2. Reference content (large — this is what gets cached)
#
# The cache_control marker goes on the LAST block so the entire prefix —
# identity + reference — is cached as one unit. Within a single run, the
# first call writes the cache and subsequent same-task calls read it.


def _system_clean() -> list[dict]:
    identity = (
        "You are an editorial assistant for the RAC Hub. Your job is to clean "
        "dictated text for staff submissions, removing dictation artefacts and "
        "informal-writing artefacts WITHOUT paraphrasing, reordering, or "
        "altering the submitter's voice.\n\n"
        "**Hard rules — non-negotiable:**\n"
        "- Never paraphrase or 'improve' the writing.\n"
        "- Never reorder sentences.\n"
        "- Never add information that wasn't in the submission.\n"
        "- Never alter proper names exactly as written.\n"
        "- Never alter Yolŋu words or any non-English content.\n"
        "- Never 'fix' Aboriginal English or Australian vernacular that's part of voice.\n"
        "- The most sophisticated thing you can do is sometimes nothing. If the "
        "  text reads cleanly already, set verbatim=true and pass it through.\n\n"
        "Output via the structured-output schema. Set the integer counters "
        "honestly — they feed an AdminNote summarising what changed.\n\n"
        "Reference material (cleaning rules + voice guide) follows. Apply the "
        "rules in the order they appear.\n"
    )
    reference = (
        "# Text cleaning rules\n\n"
        f"{_TEXT_CLEANING_RULES}\n\n"
        "---\n\n"
        "# RAC voice guide (for tone awareness while cleaning)\n\n"
        f"{_RAC_VOICE_GUIDE}\n"
    )
    return [
        {"type": "text", "text": identity},
        {"type": "text", "text": reference, "cache_control": {"type": "ephemeral"}},
    ]


def _system_title() -> list[dict]:
    identity = (
        "You are an editorial assistant for the RAC Hub. Generate a title for "
        "a story when the submitter left the title field blank.\n\n"
        "**Constraints:**\n"
        "- 2–6 words.\n"
        "- Sentence case (not Title Case unless a proper noun is in there).\n"
        "- No emoji. No clickbait. No 'breaking', 'amazing', etc.\n"
        "- Lead with the most concrete element — a name, a project, an action.\n"
        "- If the story has a real event/project name, use it verbatim. Don't "
        "  invent a description for something that already has a title.\n\n"
        "Cross-check: would your title look at home next to 'Yanawal Kitchen' "
        "or 'Tripod does it Again!'? If it feels marketing-flavoured, redo.\n\n"
        "Output via the structured-output schema.\n\n"
        "Reference material (real published titles + voice guide) follows.\n"
    )
    reference = (
        "# Example titles (real published RAC titles, with annotations)\n\n"
        f"{_EXAMPLE_TITLES}\n\n"
        "---\n\n"
        "# RAC voice guide\n\n"
        f"{_RAC_VOICE_GUIDE}\n"
    )
    return [
        {"type": "text", "text": identity},
        {"type": "text", "text": reference, "cache_control": {"type": "ephemeral"}},
    ]


def _system_highlight() -> list[dict]:
    identity = (
        "You are an editorial assistant for the RAC Hub. Generate a highlight "
        "(a short hook line) for a story when the submitter left the highlight "
        "field blank.\n\n"
        "**Constraints:**\n"
        "- Typically 5–15 words; up to 30 for multi-event recaps.\n"
        "- Warm, specific, matches the feeling of the story (pride, joy, "
        "  welcome, progress, concern for safety).\n"
        "- Optional: a single trailing emoji if it adds genuine meaning. "
        "  Skip if uncertain.\n"
        "- The highlight conveys the FEELING; the title states the topic.\n"
        "- Plain factual highlights are fine ('Photos from the event at the "
        "  town hall.') — don't manufacture poetry where none is needed.\n\n"
        "Output via the structured-output schema.\n\n"
        "Reference material (real published highlights + voice guide) follows.\n"
    )
    reference = (
        "# Example highlights (real published RAC highlights, with annotations)\n\n"
        f"{_EXAMPLE_HIGHLIGHTS}\n\n"
        "---\n\n"
        "# RAC voice guide\n\n"
        f"{_RAC_VOICE_GUIDE}\n"
    )
    return [
        {"type": "text", "text": identity},
        {"type": "text", "text": reference, "cache_control": {"type": "ephemeral"}},
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _parse(
    *,
    system: list[dict],
    user_message: str,
    output_format: type[BaseModel],
) -> Any:
    """Wrap messages.parse for the three call sites.

    Returns the parsed Pydantic instance. Raises if parsing fails or the
    model refused.
    """
    client = _get_client()
    response = client.messages.parse(
        model=_model(),
        max_tokens=_max_tokens(),
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user_message}],
        output_format=output_format,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(
            "Claude refused the request — unusual for editorial cleanup. "
            "Inspect the submission for unexpected content."
        )
    if response.parsed_output is None:
        raise RuntimeError(
            f"Claude returned a {response.stop_reason} stop reason with no parseable output."
        )
    return response.parsed_output


def clean_text(submission_text: str) -> CleanedText:
    """Apply the cleaning rules to a submission's body text."""
    user = (
        "Clean the following dictated text from a staff submission. Apply the "
        "cleaning rules in the order they appear in the reference. If the text "
        "is already clean, return it verbatim with verbatim=true.\n\n"
        "<submission_text>\n"
        f"{submission_text}\n"
        "</submission_text>"
    )
    return _parse(system=_system_clean(), user_message=user, output_format=CleanedText)


def generate_title(cleaned_text: str) -> GeneratedTitle:
    """Generate a title for a story from its cleaned body text."""
    user = (
        "Generate a title for the following story. Use the cleaned text "
        "(not the original) as your basis. Match the patterns in the "
        "reference examples.\n\n"
        "<story>\n"
        f"{cleaned_text}\n"
        "</story>"
    )
    return _parse(system=_system_title(), user_message=user, output_format=GeneratedTitle)


def generate_highlight(cleaned_text: str, title: str) -> GeneratedHighlight:
    """Generate a highlight (hook line) for a story.

    The title is passed in as additional context — sometimes the highlight
    plays off the title (e.g. title 'Yanawal Kitchen' + highlight 'She's a
    beauty!') and the model benefits from seeing the title to avoid
    duplicating it.
    """
    user = (
        "Generate a highlight (short hook line) for the following story. "
        "Match the patterns in the reference examples — convey the FEELING. "
        "Don't repeat or paraphrase the title.\n\n"
        f"<title>{title}</title>\n\n"
        "<story>\n"
        f"{cleaned_text}\n"
        "</story>"
    )
    return _parse(
        system=_system_highlight(),
        user_message=user,
        output_format=GeneratedHighlight,
    )
