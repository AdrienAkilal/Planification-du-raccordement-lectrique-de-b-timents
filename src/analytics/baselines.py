# src/analysis/baselines.py
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

def compute_kpis(df_enrich: pd.DataFrame) -> dict:
    # sécurise type_infra pour éviter “nan”
    df = df_enrich.copy()
    df["type_infra"] = df["type_infra"].fillna("inconnu")

    by_type = (
        df.groupby("type_infra", dropna=False)
          .agg(longueur=("longueur","sum"),
               cout=("cost_total","sum"),
               temps_h=("time_total_h","sum"))
          .reset_index()
    )

    total = {
        "longueur_totale": float(by_type["longueur"].sum()),
        "cout_total": float(by_type["cout"].sum()),
        "temps_total_h": float(by_type["temps_h"].sum()),
        "repartition_type": by_type.to_dict(orient="records"),
    }
    return total

def save_kpis(kpis: dict, out_path: str | Path) -> Path:
    p = Path(out_path); p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(kpis, f, ensure_ascii=False, indent=2)
    return p
