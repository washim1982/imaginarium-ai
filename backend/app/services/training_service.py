import os
from datetime import datetime
import json

def _ensure_dir(path: str):
    import os
    os.makedirs(path, exist_ok=True)

def save_pairs_to_file(pairs: list[dict], fmt: str = "json") -> str:
    """Persist generated Q/A pairs under /app/training_data and return filepath.

    fmt: 'json' or 'csv'
    """
    base_dir = "/app/training_data"
    _ensure_dir(base_dir)
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    fmt = (fmt or "json").lower()
    if fmt not in ("json", "csv"):
        fmt = "json"
    out_path = os.path.join(base_dir, f"sql_pairs_{ts}.{fmt}")
    if fmt == "json":
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(pairs, f, ensure_ascii=False, indent=2)
    else:
        import csv
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["question", "sql"])  # header
            for p in pairs:
                w.writerow([p.get("q", ""), p.get("a", "")])
    return out_path

# -------------------------------------------------------------------
# SQL TRAINER
# -------------------------------------------------------------------

async def train_sql_model(schema: dict, count: int | None = None, placeholders: bool = True):
    """
    Simulate SQL trainer — generates example question/SQL pairs.
    """
    try:
        tables = list(schema.get("tables", {}).keys())
        if not tables:
            return [{"q": "No tables found in schema.", "a": ""}]
        pairs = []
        for table, columns in schema["tables"].items():
            cols = ", ".join(columns)
            q1 = f"Show all records from {table}"
            a1 = f"SELECT {cols or '*'} FROM {table};"
            q2 = f"Count total records in {table}"
            a2 = f"SELECT COUNT(*) AS total FROM {table};"
            q3 = f"Find average of numeric columns in {table}"
            avg_cols = [c for c in columns if any(keyword in c.lower() for keyword in ["price", "amount", "score", "total", "count", "age"])]
            if avg_cols:
                selects = ", ".join([f"AVG({c}) AS avg_{c}" for c in avg_cols])
                a3 = f"SELECT {selects} FROM {table};"
            else:
                a3 = f"-- Add numeric columns in {table} to compute averages"
            q4 = f"Group {table} records by a categorical column"
            group_col = columns[0] if columns else "category"
            a4 = f"SELECT {group_col}, COUNT(*) AS count\nFROM {table}\nGROUP BY {group_col};"

            pairs.extend([
                {"q": q1, "a": a1},
                {"q": q2, "a": a2},
                {"q": q3, "a": a3},
                {"q": q4, "a": a4},
            ])

            # Optional extra pairs with placeholders
            if placeholders:
                num_cols = [c for c in columns if any(k in c.lower() for k in ["price", "amount", "score", "total", "count", "age", "id"]) ]
                date_cols = [c for c in columns if any(k in c.lower() for k in ["date", "time", "created", "updated"]) ]
                text_cols = [c for c in columns if c.lower() not in num_cols]

                if num_cols:
                    c = num_cols[0]
                    pairs.append({
                        "q": f"Find {table} rows where {c} > a threshold",
                        "a": f"SELECT * FROM {table} WHERE {c} > :min_{c};"
                    })
                    pairs.append({
                        "q": f"Filter {table} by {c} range",
                        "a": f"SELECT * FROM {table} WHERE {c} BETWEEN :min_{c} AND :max_{c};"
                    })
                if date_cols:
                    dc = date_cols[0]
                    pairs.append({
                        "q": f"Get {table} between two dates by {dc}",
                        "a": f"SELECT * FROM {table} WHERE {dc} BETWEEN :start_{dc} AND :end_{dc};"
                    })
                if text_cols:
                    tc = text_cols[0]
                    pairs.append({
                        "q": f"Search {table} by {tc} keyword",
                        "a": f"SELECT * FROM {table} WHERE {tc} LIKE CONCAT('%', :kw_{tc}, '%');"
                    })
        # Respect requested count if provided (best-effort slicing)
        if isinstance(count, int) and count > 0:
            return pairs[:count]
        return pairs
    except Exception as e:
        raise Exception(f"Error generating SQL pairs: {e}")


# -------------------------------------------------------------------
# CUSTOM MODEL TRAINER
# -------------------------------------------------------------------

async def train_custom_model(model_name: str, file_name: str):
    """
    Simulate custom model training (LoRA or fine-tuning).
    This only mocks behavior for development/testing.
    """
    try:
        # Simulate creation of a LoRA model file
        save_dir = "/app/lora_models"
        os.makedirs(save_dir, exist_ok=True)
        out_file = os.path.join(
            save_dir, f"{model_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.lora"
        )
        with open(out_file, "w") as f:
            f.write(f"Simulated trained model from {file_name}")
        return {
            "message": f"Custom model '{model_name}' trained successfully (mock).",
            "adapter_path": out_file,
        }
    except Exception as e:
        raise Exception(f"Error simulating custom model training: {e}")
