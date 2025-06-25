# app/interaction_logger.py
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

LOG_PATH = Path("logs/interactions.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def log_interaction(query: Optional[str], result_ids: list[str], doc_id: Optional[str] = None):
    entry = {
        "timestamp": datetime.now().isoformat(),
    }
    if query:
        entry["query"] = query
    if result_ids:
        entry["result_ids"] = result_ids
    if doc_id:
        entry["doc_id"] = doc_id

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")