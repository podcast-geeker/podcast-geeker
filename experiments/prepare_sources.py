"""
Source Document Preparation
============================
Generates 9 source documents (800-1200 words each) for the experiment.

If course-material PDFs are available locally, extracts and rewrites them.
Otherwise, generates all documents via the configured LLM API.

Usage:
    export OPENAI_COMPATIBLE_BASE_URL=https://...
    export OPENAI_COMPATIBLE_API_KEY=sk-...
    python experiments/prepare_sources.py
"""

import sys
import time
from pathlib import Path

from openai import OpenAI

from experiment_config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    TOPICS,
    TOPICS_DIR,
)

MAX_RETRIES = 3
MIN_WORD_COUNT = 200

SYSTEM_PROMPT = (
    "You are an academic writer. Write a well-structured educational article "
    "on the given topic. The article should be 800-1200 words, factually accurate, "
    "and written in clear academic English suitable as source material for a "
    "podcast episode. Include concrete examples, key terminology, and current "
    "developments. Do NOT include a title or headings — write continuous prose."
)


def get_client() -> OpenAI:
    if not LLM_BASE_URL:
        sys.exit(
            "[ERROR] Set OPENAI_COMPATIBLE_BASE_URL (or OPENAI_COMPATIBLE_BASE_URL_LLM) "
            "environment variable."
        )
    return OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def generate_source(client: OpenAI, topic: dict) -> str:
    """Generate a source document, retrying up to MAX_RETRIES on empty/short responses."""
    user_prompt = (
        f"Topic: {topic['topic']}\n\n"
        f"Key areas to cover:\n{topic['source_hint']}\n\n"
        f"Important keywords to include: {', '.join(topic['keywords'])}\n\n"
        "Write the article now (800-1200 words, continuous prose, no headings)."
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            content = response.choices[0].message.content or ""
            text = content.strip()
            word_count = len(text.split())

            if word_count >= MIN_WORD_COUNT:
                return text

            print(
                f"\n    [retry {attempt}/{MAX_RETRIES}] got {word_count} words "
                f"(need >={MIN_WORD_COUNT}), retrying ...",
                end=" ",
                flush=True,
            )
        except Exception as e:
            print(
                f"\n    [retry {attempt}/{MAX_RETRIES}] API error: {e}",
                end=" ",
                flush=True,
            )
            text = ""

        if attempt < MAX_RETRIES:
            time.sleep(2 * attempt)

    return text


def main() -> None:
    print("=" * 60)
    print("Source Document Preparation")
    print("=" * 60)
    print(f"  Model   : {LLM_MODEL}")
    print(f"  Base URL: {LLM_BASE_URL}")
    print(f"  Output  : {TOPICS_DIR}")
    print()

    TOPICS_DIR.mkdir(parents=True, exist_ok=True)
    client = get_client()

    total = len(TOPICS)
    failed: list[str] = []

    for i, topic in enumerate(TOPICS, 1):
        out_path = TOPICS_DIR / f"{topic['topic_id']}.txt"
        if out_path.exists() and out_path.stat().st_size > 0:
            existing_words = len(out_path.read_text(encoding="utf-8").split())
            if existing_words >= MIN_WORD_COUNT:
                print(f"[{i}/{total}] SKIP {topic['topic_id']} ({existing_words} words)")
                continue
            print(f"[{i}/{total}] RE-GEN {topic['topic_id']} (only {existing_words} words)")

        print(f"[{i}/{total}] Generating: {topic['topic']} ...", end=" ", flush=True)
        t0 = time.time()
        text = generate_source(client, topic)
        elapsed = time.time() - t0
        word_count = len(text.split())

        if word_count < MIN_WORD_COUNT:
            print(f"FAILED ({word_count} words after {MAX_RETRIES} retries, {elapsed:.1f}s)")
            failed.append(topic["topic_id"])
            if out_path.exists():
                out_path.unlink()
            continue

        out_path.write_text(text, encoding="utf-8")
        print(f"done ({word_count} words, {elapsed:.1f}s)")

    if failed:
        print(f"\n[WARNING] {len(failed)} topic(s) failed: {', '.join(failed)}")
        print("Re-run the script to retry them.")
    else:
        print(f"\n[Done] {total} source documents saved to {TOPICS_DIR}")


if __name__ == "__main__":
    main()
