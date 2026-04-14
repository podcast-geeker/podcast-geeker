import json
import os

RESULT_PATH = "./experiments/evaluation/data"
RESULT_NAME = "evaluate.json"

# Read JSON file
with open(os.path.join(RESULT_PATH, RESULT_NAME), "r", encoding="utf-8") as f:
    evaluate = json.load(f)

# Define metrics list
metrics = [
    "avg_distinct_1",
    "avg_distinct_2",
    "avg_rouge_l",
    "avg_perplexity",
    "avg_bertscore",
    "avg_latency_seconds",
    "avg_estimated_cost_usd",
]

# Create table header
header = (
    "| Model | "
    + " | ".join(
        [metric.replace("avg_", "").replace("_", " ").title() for metric in metrics]
    )
    + " |"
)
separator = "| " + " | ".join(["---" for _ in range(len(metrics) + 1)]) + " |"

# Create table content
table_rows = []
for model_name, model_data in evaluate.items():
    row_values = []
    for metric in metrics:
        if metric.startswith("avg_"):
            if metric in model_data:
                value = model_data[metric]
            elif "metrics" in model_data and metric in model_data["metrics"]:
                value = model_data["metrics"][metric]
            else:
                value = "N/A"
        else:
            value = "N/A"

        # Format value
        if isinstance(value, float):
            if metric == "avg_estimated_cost_usd":
                row_values.append(f"{value:.6f}")
            elif metric == "avg_latency_seconds":
                row_values.append(f"{value:.2f}")
            else:
                row_values.append(f"{value:.4f}")
        else:
            row_values.append(str(value))

    row = f"| {model_name} | " + " | ".join(row_values) + " |"
    table_rows.append(row)

# Combine complete Markdown table
markdown_table = "\n".join([header, separator] + table_rows)

# Output result
print(markdown_table)

# Save to file
output_path = os.path.join(RESULT_PATH, "evaluation_results.md")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(markdown_table)

print(f"\nTable saved to: {output_path}")
