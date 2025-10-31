from pathlib import Path
import pandas as pd
import json
from datetime import datetime

def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds").replace(":","-")

def save_csv(df: pd.DataFrame, base: str | Path) -> Path:
    p = Path(f"{base}_{_ts()}.csv"); p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False); return p

def save_json(obj: dict, base: str | Path) -> Path:
    p = Path(f"{base}_{_ts()}.json"); p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=2)
    return p
