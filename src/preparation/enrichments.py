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
    "worker_eur_per_hour": 37.5,
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

    # Mapping des clés YAML aux noms attendus
    if "units" in cfg:
        mat = cfg["units"].get("cost_per_m", cfg.get("material_eur_per_m", {}))
        hpm = cfg["units"].get("hours_per_m", cfg.get("hours_per_m", {}))
    else:
        mat = cfg.get("material_eur_per_m", {})
        hpm = cfg.get("hours_per_m", {})
    
    if "workforce" in cfg:
        crew_max = int(cfg["workforce"].get("max_workers_per_infra", cfg.get("crew_max_per_infra", 4)))
        hourly = float(cfg["workforce"].get("worker_wage_per_hour", cfg.get("worker_eur_per_hour", 37.5)))
    else:
        crew_max = int(cfg.get("crew_max_per_infra", 4))
        hourly = float(cfg.get("worker_eur_per_hour", 37.5))

    # Utilise type_infra_src (type physique) pour les calculs de coûts
    # type_infra contient l'état (infra_intacte, a_remplacer)
    type_col = "type_infra_src" if "type_infra_src" in df.columns else "type_infra"
    df[type_col] = df[type_col].map(_normalize_type)

    df["hours_per_m"] = df[type_col].map(hpm)
    df["cost_per_m"]  = df[type_col].map(mat)

    unknown_mask = df["hours_per_m"].isna() | df["cost_per_m"].isna()
    if unknown_mask.any():
        df.loc[unknown_mask, type_col] = df.loc[unknown_mask, type_col].fillna("inconnu")
        df["hours_per_m"] = df["hours_per_m"].fillna(0.0)
        df["cost_per_m"]  = df["cost_per_m"].fillna(0.0)
        top = df.loc[unknown_mask, type_col].value_counts().head(10).to_dict()
        print(f"⚠️ {int(unknown_mask.sum())} lignes avec {type_col} inconnu → coûts/temps=0. Top: {top}")

    # hypothèse: 1 <= crew_effectif <= crew_max (si tu veux modéliser un crew variable, ajoute une colonne)
    crew =  max(1, min(crew_max, crew_max))  # par défaut on sature à crew_max

    df["man_hours"]     = df["longueur"] * df["hours_per_m"]
    df["time_total_h"]  = df["man_hours"] / crew
    df["material_cost"] = df["longueur"] * df["cost_per_m"]
    df["labor_cost"]    = df["man_hours"] * hourly
    df["cost_total"]    = df["material_cost"] + df["labor_cost"]

    # Flag de réparations: si coût/temps > 0, on considère à réparer (vs "infra_intacte" si tu as le champ)
    if "infra_type" in df.columns:
        # quand fourni, "infra_intacte" prime
        mask_intact = (df["infra_type"].astype(str).str.lower() == "infra_intacte")
        df["a_reparer"] = (~mask_intact & (df["cost_total"] > 0)).astype(int)
    else:
        df["a_reparer"] = (df["cost_total"] > 0).astype(int)

    # Flag hôpital : si type_batiment contient "hôpital" ou "hopital"
    if "type_batiment" in df.columns:
        df["is_hospital"] = df["type_batiment"].astype(str).str.lower().str.contains("h[oô]pital", regex=True, na=False).astype(int)
    else:
        df["is_hospital"] = 0

    return df
