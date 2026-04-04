"""
Experiment Transcript Generator
================================
Generates podcast dialogue transcripts for experiment configurations A, B,
B_review, and Reference using the configured LLM API (glm-5-turbo by default).

Each result is saved as a JSON file with 4 embedded system metrics:
  - latency_seconds
  - input_tokens / output_tokens / total_tokens
  - estimated_cost_usd
  - peak_gpu_memory_gb  (null for API configs)

Usage:
    # Generate all configs for all topics
    python experiments/generate_transcript.py --config all

    # Single config, single domain
    python experiments/generate_transcript.py --config A --topics tech

    # Specific topic
    python experiments/generate_transcript.py --config B --topic-id tech_1_transformer_attention

Environment:
    OPENAI_COMPATIBLE_BASE_URL  (or OPENAI_COMPATIBLE_BASE_URL_LLM)
    OPENAI_COMPATIBLE_API_KEY   (or OPENAI_COMPATIBLE_API_KEY_LLM)
    EXPERIMENT_LLM_MODEL        (default: glm-5-turbo)
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from experiment_config import (
    BASELINE_API_DIR,
    INPUT_COST_PER_1K,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    MULTI_AGENT_API_DIR,
    MULTI_AGENT_REVIEW_DIR,
    OUTPUT_COST_PER_1K,
    REFERENCE_DIR,
    TOPICS,
    TOPICS_DIR,
)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

BASELINE_SYSTEM = (
    "You are a podcast script writer. Given source material, write a natural "
    "two-person podcast conversation between a Host and an Expert."
)

BASELINE_USER = """\
Topic: {topic}

Source material:
{source_text}

Requirements:
- Generate exactly 10 turns (5 host lines + 5 expert lines, strictly alternating, starting with host).
- The Host asks engaging questions and guides the conversation.
- The Expert provides insightful, accurate answers grounded in the source material.
- Each turn: 1-3 sentences, natural and suitable for audio.

Return ONLY a JSON array (no markdown fences). Each element: {{"speaker": "host" or "expert", "text": "..."}}
"""

REFERENCE_SYSTEM = (
    "You are an award-winning podcast producer at NPR. Create a gold-standard "
    "two-person podcast conversation that demonstrates exceptional broadcast quality."
)

REFERENCE_USER = """\
Topic: {topic}

Source material:
{source_text}

Requirements:
- Generate exactly 10 turns (5 host + 5 expert, alternating, host first).
- NPR-level quality: warm, professional, intellectually curious.
- Host: asks brilliant questions that reveal depth, uses callbacks to previous answers.
- Expert: provides expert-level insights with vivid analogies and real-world examples.
- Natural rhythm: varies sentence length, includes brief reactions.
- Each turn: 2-4 sentences, conversational yet substantive.

Return ONLY a JSON array (no markdown fences). Each element: {{"speaker": "host" or "expert", "text": "..."}}
"""

HOST_SYSTEM = (
    "You are a podcast host having a conversation with an expert guest. "
    "Your style is warm, curious, and engaging."
)

HOST_USER = """\
Topic: {topic}

Source material (excerpt):
{source_excerpt}

Recent dialogue:
{recent_turns}

Speak your NEXT LINE ONLY as the Host (~30-50 English words):
- Opening: introduce or frame the topic.
- Middle: ask the Expert a clear question or follow up on their last answer.
- Closing (turn 5): steer toward a concise wrap-up.

Current turn: {turn_num} of 5.

Output ONLY the spoken line — no name prefix, no quotes, no stage directions.
"""

EXPERT_SYSTEM = (
    "You are a knowledgeable podcast guest expert. "
    "Your style is insightful, concise, and uses concrete examples."
)

EXPERT_USER = """\
Topic: {topic}

Source material (excerpt):
{source_excerpt}

Recent dialogue:
{recent_turns}

The Host just said:
"{host_last_line}"

Respond with your NEXT LINE ONLY as the Expert (~40-60 English words):
- Answer the Host directly.
- Bring in concrete insight, analogy, or example from the source material.

Output ONLY the spoken line — no name prefix, no quotes, no stage directions.
"""

REVIEW_SYSTEM = (
    "You are a strict editorial reviewer for a two-speaker podcast segment."
)

REVIEW_USER = """\
Topic: {topic}

Dialogue to review:
{dialogue_text}

Score the exchange on:
- Relevance (0-3): stays on topic.
- Flow (0-3): natural back-and-forth.
- Depth (0-4): substantive, not filler.

Total raw points 0-10. Convert to score = (raw / 10) as float 0.0-1.0.
Decide passed: true if score >= 0.65.

Respond with ONLY a JSON object (no markdown fences):
{{"score": <float>, "feedback": "<short actionable notes>", "passed": <true|false>}}
"""

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_MAX_REVIEW_RETRIES = 2

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def _parse_turns(text: str) -> list[dict]:
    """Extract a JSON array of turns from LLM output, tolerating markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    match = _JSON_ARRAY_RE.search(cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    print("  [WARN] Could not parse JSON turns, returning raw text as single turn")
    return [{"speaker": "host", "text": cleaned}]


def _compute_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000 * INPUT_COST_PER_1K) + (
        output_tokens / 1000 * OUTPUT_COST_PER_1K
    )


def _format_recent(turns: list[dict]) -> str:
    if not turns:
        return "(conversation start)"
    lines = []
    for t in turns[-6:]:
        label = "Host" if t["speaker"] == "host" else "Expert"
        lines.append(f"{label}: {t['text']}")
    return "\n".join(lines)


def _build_result(
    config: str,
    topic: dict,
    turns: list[dict],
    metrics: dict,
) -> dict:
    return {
        "config": config,
        "topic_id": topic["topic_id"],
        "topic": topic["topic"],
        "domain": topic["domain"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": LLM_MODEL,
        "turns": turns,
        "metrics": metrics,
    }


# ---------------------------------------------------------------------------
# Config A — Baseline (single prompt)
# ---------------------------------------------------------------------------

def generate_baseline(client: OpenAI, topic: dict, source_text: str) -> dict:
    t0 = time.time()

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": BASELINE_SYSTEM},
            {
                "role": "user",
                "content": BASELINE_USER.format(
                    topic=topic["topic"], source_text=source_text[:6000]
                ),
            },
        ],
        temperature=0.7,
        max_tokens=2000,
    )

    latency = time.time() - t0
    usage = response.usage
    turns = _parse_turns(response.choices[0].message.content)

    return _build_result(
        "A",
        topic,
        turns,
        {
            "latency_seconds": round(latency, 2),
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "estimated_cost_usd": round(
                _compute_cost(usage.prompt_tokens, usage.completion_tokens), 6
            ),
            "peak_gpu_memory_gb": None,
        },
    )


# ---------------------------------------------------------------------------
# Config B — Multi-Agent (host → expert) × 5, no review
# ---------------------------------------------------------------------------

def _run_multi_agent_dialogue(
    client: OpenAI, topic: dict, source_excerpt: str
) -> tuple[list[dict], int, int]:
    """Run (host → expert) × 5 and return (turns, input_tokens, output_tokens)."""
    turns: list[dict] = []
    total_input = 0
    total_output = 0

    for turn_num in range(1, 6):
        host_resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": HOST_SYSTEM},
                {
                    "role": "user",
                    "content": HOST_USER.format(
                        topic=topic["topic"],
                        source_excerpt=source_excerpt,
                        recent_turns=_format_recent(turns),
                        turn_num=turn_num,
                    ),
                },
            ],
            temperature=0.7,
            max_tokens=200,
        )
        host_line = host_resp.choices[0].message.content.strip().strip('"').strip("'")
        total_input += host_resp.usage.prompt_tokens
        total_output += host_resp.usage.completion_tokens
        turns.append({"speaker": "host", "text": host_line})

        expert_resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": EXPERT_SYSTEM},
                {
                    "role": "user",
                    "content": EXPERT_USER.format(
                        topic=topic["topic"],
                        source_excerpt=source_excerpt,
                        recent_turns=_format_recent(turns),
                        host_last_line=host_line,
                    ),
                },
            ],
            temperature=0.7,
            max_tokens=250,
        )
        expert_line = (
            expert_resp.choices[0].message.content.strip().strip('"').strip("'")
        )
        total_input += expert_resp.usage.prompt_tokens
        total_output += expert_resp.usage.completion_tokens
        turns.append({"speaker": "expert", "text": expert_line})

    return turns, total_input, total_output


def generate_multi_agent(client: OpenAI, topic: dict, source_text: str) -> dict:
    t0 = time.time()
    turns, total_input, total_output = _run_multi_agent_dialogue(
        client, topic, source_text[:4000]
    )
    latency = time.time() - t0

    return _build_result(
        "B",
        topic,
        turns,
        {
            "latency_seconds": round(latency, 2),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "estimated_cost_usd": round(
                _compute_cost(total_input, total_output), 6
            ),
            "peak_gpu_memory_gb": None,
        },
    )


# ---------------------------------------------------------------------------
# Config B_review — Multi-Agent + Quality Review (ablation)
# ---------------------------------------------------------------------------

def _parse_review(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = _JSON_OBJECT_RE.search(cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {"score": 0.5, "feedback": "parse_failure", "passed": True}


def generate_multi_agent_with_review(
    client: OpenAI, topic: dict, source_text: str
) -> dict:
    source_excerpt = source_text[:4000]
    total_input = 0
    total_output = 0
    review = {"score": 0.0, "passed": False}

    t0 = time.time()

    for attempt in range(1 + _MAX_REVIEW_RETRIES):
        turns, inp, out = _run_multi_agent_dialogue(client, topic, source_excerpt)
        total_input += inp
        total_output += out

        dialogue_text = "\n".join(
            f"{'Host' if t['speaker'] == 'host' else 'Expert'}: {t['text']}"
            for t in turns
        )
        review_resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM},
                {
                    "role": "user",
                    "content": REVIEW_USER.format(
                        topic=topic["topic"], dialogue_text=dialogue_text
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=300,
        )
        total_input += review_resp.usage.prompt_tokens
        total_output += review_resp.usage.completion_tokens

        review = _parse_review(review_resp.choices[0].message.content)
        if review.get("passed", False):
            break
        if attempt < _MAX_REVIEW_RETRIES:
            print(
                f"[review] score={review.get('score', '?')}, retrying "
                f"({attempt + 1}/{_MAX_REVIEW_RETRIES})...",
                end=" ",
                flush=True,
            )

    latency = time.time() - t0

    return _build_result(
        "B_review",
        topic,
        turns,
        {
            "latency_seconds": round(latency, 2),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "estimated_cost_usd": round(
                _compute_cost(total_input, total_output), 6
            ),
            "peak_gpu_memory_gb": None,
            "review_score": review.get("score"),
            "review_attempts": attempt + 1,
        },
    )


# ---------------------------------------------------------------------------
# Reference — NPR-style gold standard
# ---------------------------------------------------------------------------

def generate_reference(client: OpenAI, topic: dict, source_text: str) -> dict:
    t0 = time.time()

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": REFERENCE_SYSTEM},
            {
                "role": "user",
                "content": REFERENCE_USER.format(
                    topic=topic["topic"], source_text=source_text[:6000]
                ),
            },
        ],
        temperature=0.7,
        max_tokens=2500,
    )

    latency = time.time() - t0
    usage = response.usage
    turns = _parse_turns(response.choices[0].message.content)

    return _build_result(
        "ref",
        topic,
        turns,
        {
            "latency_seconds": round(latency, 2),
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "estimated_cost_usd": round(
                _compute_cost(usage.prompt_tokens, usage.completion_tokens), 6
            ),
            "peak_gpu_memory_gb": None,
        },
    )


# ---------------------------------------------------------------------------
# CLI & main
# ---------------------------------------------------------------------------

CONFIG_MAP = {
    "A": ("baseline_api", BASELINE_API_DIR, generate_baseline),
    "B": ("multi_agent_api", MULTI_AGENT_API_DIR, generate_multi_agent),
    "B_review": ("multi_agent_review", MULTI_AGENT_REVIEW_DIR, generate_multi_agent_with_review),
    "ref": ("reference", REFERENCE_DIR, generate_reference),
}

DOMAIN_FILTER = {
    "tech": "technology",
    "hum": "humanities",
    "med": "medicine",
    "all": None,
}


def _select_topics(args) -> list[dict]:
    if args.topic_id:
        matched = [t for t in TOPICS if t["topic_id"] == args.topic_id]
        if not matched:
            sys.exit(f"[ERROR] Unknown topic_id: {args.topic_id}")
        return matched
    domain = DOMAIN_FILTER.get(args.topics)
    if domain is None:
        return list(TOPICS)
    return [t for t in TOPICS if t["domain"] == domain]


def _load_source(topic: dict) -> str:
    path = TOPICS_DIR / f"{topic['topic_id']}.txt"
    if not path.exists():
        sys.exit(
            f"[ERROR] Source file missing: {path}\n"
            "  → Run prepare_sources.py first."
        )
    return path.read_text(encoding="utf-8")


def run(args) -> None:
    configs = list(CONFIG_MAP.keys()) if args.config == "all" else [args.config]
    topics = _select_topics(args)

    print("=" * 60)
    print("Experiment Transcript Generator")
    print("=" * 60)
    print(f"  Model   : {LLM_MODEL}")
    print(f"  Base URL: {LLM_BASE_URL}")
    print(f"  Configs : {configs}")
    print(f"  Topics  : {len(topics)}")
    print()

    if not LLM_BASE_URL:
        sys.exit(
            "[ERROR] Set OPENAI_COMPATIBLE_BASE_URL (or OPENAI_COMPATIBLE_BASE_URL_LLM) "
            "environment variable."
        )

    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

    for cfg_key in configs:
        label, out_dir, gen_fn = CONFIG_MAP[cfg_key]
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"--- Config {cfg_key} ({label}) ---")

        for i, topic in enumerate(topics, 1):
            out_path = out_dir / f"{topic['topic_id']}.json"
            if out_path.exists() and not args.overwrite:
                print(f"  [{i}/{len(topics)}] SKIP {topic['topic_id']} (exists)")
                continue

            source_text = _load_source(topic)
            print(
                f"  [{i}/{len(topics)}] {topic['topic_id']} ...",
                end=" ",
                flush=True,
            )

            result = gen_fn(client, topic, source_text)

            out_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            m = result["metrics"]
            print(
                f"done  latency={m['latency_seconds']:.1f}s  "
                f"tokens={m['total_tokens']}  "
                f"cost=${m['estimated_cost_usd']:.4f}"
            )

        print()

    print("[Done] All transcripts generated.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate experiment transcripts (Config A/B/B_review/ref)"
    )
    parser.add_argument(
        "--config",
        choices=["A", "B", "B_review", "ref", "all"],
        default="all",
        help="Which config to run (default: all)",
    )
    parser.add_argument(
        "--topics",
        choices=["tech", "hum", "med", "all"],
        default="all",
        help="Which domain to run (default: all)",
    )
    parser.add_argument(
        "--topic-id",
        default=None,
        help="Run a single topic by ID (overrides --topics)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
