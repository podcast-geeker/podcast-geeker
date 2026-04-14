import json
import os

RESULT_PATH = "./experiments/evaluation/data"
RESULT_NAME = "evaluate.json"

# Read JSON file
with open(os.path.join(RESULT_PATH, RESULT_NAME), "r", encoding="utf-8") as f:
    evaluate = json.load(f)

# Define LLM evaluation metrics list
llm_metrics = [
    "role_consistency",
    "naturalness",
    "informativeness",
    "topic_relevance",
    "engagement",
]

# Create table header
header = (
    "| Model | "
    + " | ".join([metric.replace("_", " ").title() for metric in llm_metrics])
    + " |"
)
separator = "| " + " | ".join(["---" for _ in range(len(llm_metrics) + 1)]) + " |"

# Create table content
table_rows = []
for model_name, model_data in evaluate.items():
    row_values = []
    for metric in llm_metrics:
        if "llm_evaluation" in model_data and metric in model_data["llm_evaluation"]:
            value = model_data["llm_evaluation"][metric]
            # Format value, keep 3 decimal places
            if isinstance(value, float):
                row_values.append(f"{value:.3f}")
            else:
                row_values.append(str(value))
        else:
            row_values.append("N/A")

    row = f"| {model_name} | " + " | ".join(row_values) + " |"
    table_rows.append(row)

# Combine complete Markdown table
markdown_table = "\n".join([header, separator] + table_rows)

# Output result
print(markdown_table)

# Save to file
output_path = os.path.join(RESULT_PATH, "llm_evaluation_results.md")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(markdown_table)

print(f"\nTable saved to: {output_path}")
