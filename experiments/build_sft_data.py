"""
Build high-quality SFT training data for QLoRA fine-tuning.

Converts API-generated dialogues (reference, multi_agent_review, multi_agent_api)
into chat-message format, pairing each dialogue with its topic source material.

Output: train_sft.json — ready to upload to Colab.

Usage:
    python experiments/build_sft_data.py
"""

import json
import glob
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / "evaluation" / "data"
TOPICS_DIR = DATA_DIR / "topics"
OUTPUT_FILE = Path(__file__).parent / "train_sft.json"

CONFIGS_TO_USE = ["reference", "multi_agent_api", "multi_agent_review"]

SYSTEM_PROMPT_TEMPLATE = (
    "You are a podcast script writer. Given source material, write a natural "
    "two-person podcast conversation between a Host and an Expert.\n\n"
    "Topic: {topic}\n\n"
    "Source material:\n{source_text}"
)

MIN_TURNS = 4


def load_topic_sources() -> dict[str, str]:
    sources = {}
    for f in TOPICS_DIR.glob("*.txt"):
        topic_id = f.stem
        sources[topic_id] = f.read_text().strip()
    return sources


def clean_turns(turns: list[dict]) -> list[dict]:
    """Keep only valid turns up to the first empty-text turn, ensuring pairs."""
    cleaned = []
    for t in turns:
        text = (t.get("text") or "").strip()
        if not text:
            break
        speaker = t.get("speaker", "").lower()
        if speaker not in ("host", "expert"):
            break
        cleaned.append({"speaker": speaker, "text": text})

    if len(cleaned) % 2 != 0:
        cleaned = cleaned[:-1]
    return cleaned


def turns_to_messages(topic: str, source_text: str, turns: list[dict]) -> list[dict]:
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT_TEMPLATE.format(
                topic=topic, source_text=source_text[:4000]
            ),
        }
    ]
    for t in turns:
        role = "user" if t["speaker"] == "host" else "assistant"
        messages.append({"role": role, "content": t["text"]})
    return messages


def main():
    topic_sources = load_topic_sources()
    print(f"Loaded {len(topic_sources)} topic source texts")

    sft_data = []
    stats = {"total": 0, "skipped_short": 0, "skipped_no_source": 0}

    for cfg in CONFIGS_TO_USE:
        cfg_dir = DATA_DIR / cfg
        files = sorted(cfg_dir.glob("*.json"))
        cfg_added = 0

        for f in files:
            data = json.loads(f.read_text())
            topic_id = data.get("topic_id", f.stem)
            topic = data.get("topic", topic_id)
            stats["total"] += 1

            source_text = topic_sources.get(topic_id)
            if not source_text:
                stats["skipped_no_source"] += 1
                print(f"  [SKIP] {cfg}/{f.name}: no source text for {topic_id}")
                continue

            turns = clean_turns(data.get("turns", []))
            if len(turns) < MIN_TURNS:
                stats["skipped_short"] += 1
                print(f"  [SKIP] {cfg}/{f.name}: only {len(turns)} clean turns")
                continue

            messages = turns_to_messages(topic, source_text, turns)
            sft_data.append({"messages": messages})
            cfg_added += 1

        print(f"[{cfg}] {cfg_added}/{len(files)} dialogues added")

    OUTPUT_FILE.write_text(json.dumps(sft_data, indent=2, ensure_ascii=False))

    print(f"\n{'='*50}")
    print(f"Total SFT samples: {len(sft_data)}")
    print(f"Skipped (too short): {stats['skipped_short']}")
    print(f"Skipped (no source): {stats['skipped_no_source']}")
    print(f"Output: {OUTPUT_FILE}")

    total_turns = sum(
        len([m for m in s["messages"] if m["role"] != "system"])
        for s in sft_data
    )
    total_words = sum(
        len(m["content"].split())
        for s in sft_data
        for m in s["messages"]
        if m["role"] != "system"
    )
    print(f"Total dialogue turns: {total_turns}")
    print(f"Total dialogue words: ~{total_words}")


if __name__ == "__main__":
    main()
