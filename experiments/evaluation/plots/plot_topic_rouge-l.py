import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from math import pi

RESULT_PATH = "./experiments/evaluation/data"
RESULT_NAME = "evaluate.json"

with open(os.path.join(RESULT_PATH, RESULT_NAME), "r", encoding="utf-8") as f:
    evaluate = json.load(f)

# Extract data
multi_agent_api_data = evaluate["multi_agent_api"]["topics"]
baseline_avg = evaluate["baseline_api"]["avg_rouge_l"]
multi_agent_review_data = evaluate["multi_agent_review"]["topics"]
multi_agent_api_avg = evaluate["multi_agent_api"]["avg_rouge_l"]

# Prepare topic names and scores
topics = list(multi_agent_api_data.keys())
multi_agent_api_scores = [multi_agent_api_data[topic]["rouge_l"] for topic in topics]
multi_agent_review_scores = [
    multi_agent_review_data[topic]["rouge_l"] for topic in topics
]


# Figure 1: multi_agent_api vs baseline_api
def plot_multi_agent_api_vs_baseline():
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(topics))
    width = 0.5

    bars = ax.bar(
        x, multi_agent_api_scores, width, label="Multi-Agent API", color="#c1d8e9"
    )
    ax.axhline(
        y=baseline_avg,
        color="#92b1d9",
        linestyle="--",
        linewidth=2,
        label=f"Baseline API Avg ({baseline_avg:.3f})",
    )

    ax.set_xlabel("Topics")
    ax.set_ylabel("ROUGE-L Score")
    ax.set_title("Multi-Agent API ROUGE-L Scores vs Baseline API Average")
    ax.set_xticks(x)
    ax.set_xticklabels(topics, rotation=45, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:.3f}",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    plt.savefig(
        os.path.join(RESULT_PATH, "multi_agent_api_vs_baseline_topic_rouge-l.png"),
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()


# Figure 2: multi_agent_review vs multi_agent_api
def plot_multi_agent_review_vs_api():
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(topics))
    width = 0.5

    bars = ax.bar(
        x, multi_agent_review_scores, width, label="Multi-Agent Review", color="#d4d4d4"
    )
    ax.axhline(
        y=multi_agent_api_avg,
        color="#c1d8e9",
        linestyle="--",
        linewidth=2,
        label=f"Multi-Agent API Avg ({multi_agent_api_avg:.3f})",
    )

    ax.set_xlabel("Topics")
    ax.set_ylabel("ROUGE-L Score")
    ax.set_title("Multi-Agent Review ROUGE-L Scores vs Multi-Agent API Average")
    ax.set_xticks(x)
    ax.set_xticklabels(topics, rotation=45, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:.3f}",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    plt.savefig(
        os.path.join(RESULT_PATH, "multi_agent_review_vs_api_topic_rouge-l.png"),
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()


# Execute plotting
plot_multi_agent_api_vs_baseline()
plot_multi_agent_review_vs_api()
