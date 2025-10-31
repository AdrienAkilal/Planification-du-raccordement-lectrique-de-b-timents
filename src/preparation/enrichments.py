# src/preparation/enrichments.py
from __future__ import annotations
import json
import yaml
import pandas as pd
from pathlib import Path

DEFAULT_COSTS = {
    "material_eur_per_m": {
        "aerien": 500.0,
        "semi-aerien": 750.0,
        "fourreau": 900.0,
    },
    "hours_per_m": {
        "aerien": 2.0,
        "semi-aerien": 4.0,
        "fourreau": 5.0,
    },
    "crew_max_per_infra": 4,
    "worker_eur_per_day8h": 300.0,
}

def _load_costs_yaml(path: str | Path | None) -> dict:
    if not path:
        return DEFAULT_COSTS
    p = Path(path)
    if not p.exists():
        print(f"⚠️ costs.yaml introuvable ({p}), usage des valeurs par défaut.")
        return DEFAULT_COSTS
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # fusion légère avec défauts
    cfg = DEFAULT_COSTS.copy()
    cfg.update(data or {})
    # compat JSON “flat”
    if "infra" in data or "batiment" in data:
        pass
    return cfg

def _normalize_type(s):
    if pd.isna(s): return None
    s = str(s).strip().lower()
    m = {
        "aérien": "aerien", "aerien": "aerien",
        "semi-aérien": "semi-aerien", "semi aerien": "semi-aerien", "semi_aerien": "semi-aerien",
        "fourreau": "fourreau", "souterrain": "fourreau", "underground": "fourreau",
    }
    return m.get(s, s)

def enrich_costs_and_flags(df: pd.DataFrame, costs_yaml: str | Path | None = None) -> pd.DataFrame:
    """
    Ajoute coûts/temps (matériel + main-d’œuvre) et flags.
    - time_total_h = (longueur * hours_per_m) / crew_effectif (borne à 1..crew_max)
    - labor_cost = man_hours * hourly_rate
    - cost_total = material_cost + labor_cost
    """
    df = df.copy()
    cfg = _load_costs_yaml(costs_yaml)

    mat = cfg["material_eur_per_m"]
    hpm = cfg["hours_per_m"]
    crew_max = int(cfg.get("crew_max_per_infra", 4))
    day8 = float(cfg.get("worker_eur_per_day8h", 300.0))
    hourly = day8 / 8.0

    df["type_infra"] = df["type_infra"].map(_normalize_type)

    df["hours_per_m"] = df["type_infra"].map(hpm)
    df["cost_per_m"]  = df["type_infra"].map(mat)

    unknown_mask = df["hours_per_m"].isna() | df["cost_per_m"].isna()
    if unknown_mask.any():
        df.loc[unknown_mask, "type_infra"] = df.loc[unknown_mask, "type_infra"].fillna("inconnu")
        df["hours_per_m"] = df["hours_per_m"].fillna(0.0)
        df["cost_per_m"]  = df["cost_per_m"].fillna(0.0)
        top = df.loc[unknown_mask, "type_infra"].value_counts().head(10).to_dict()
        print(f"⚠️ {int(unknown_mask.sum())} lignes avec type_infra inconnu → coûts/temps=0. Top: {top}")

    # hypothèse: 1 <= crew_effectif <= crew_max (si tu veux modéliser un crew variable, ajoute une colonne)
    crew =  max(1, min(crew_max, crew_max))  # par défaut on sature à crew_max

    df["man_hours"]     = df["longueur"] * df["hours_per_m"]
    df["time_total_h"]  = df["man_hours"] / crew
    df["material_cost"] = df["longueur"] * df["cost_per_m"]
    df["labor_cost"]    = df["man_hours"] * hourly
    df["cost_total"]    = df["material_cost"] + df["labor_cost"]

    # Flag de réparations: si coût/temps > 0, on considère à réparer (vs “infra_intacte” si tu as le champ)
    if "infra_type" in df.columns:
        # quand fourni, “infra_intacte” prime
        mask_intact = (df["infra_type"].astype(str).str.lower() == "infra_intacte")
        df["a_reparer"] = (~mask_intact & (df["cost_total"] > 0)).astype(int)
    else:
        df["a_reparer"] = (df["cost_total"] > 0).astype(int)

    return df
