# src/analytics/work_organizer.py
from __future__ import annotations
from pathlib import Path
from typing import Tuple, Dict, Any, List
import pandas as pd
import numpy as np
import yaml


def _load_cfg(costs_yaml: str | Path) -> Dict[str, Any]:
    p = Path(costs_yaml)
    if not p.exists():
        raise FileNotFoundError(f"Config coûts introuvable: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _collect_hospital_tasks(df_enrich: pd.DataFrame) -> pd.DataFrame:
    """Toutes les tâches (tronçons) à réparer qui alimentent un hôpital."""
    hosp = df_enrich.copy()
    hosp = hosp[hosp["is_hospital"] == 1]
    # On garde uniquement les tronçons à réparer (le reste est temps=0, coût=0)
    hosp = hosp[hosp["a_reparer"] == 1]
    # tri par coût ou au choix par temps décroissant (ici coût décroissant pour mieux ‘payer’ la phase 0)
    hosp = hosp.sort_values(["id_batiment", "cost_total", "time_total_h"], ascending=[True, False, False]).reset_index(drop=True)
    return hosp


def _collect_non_hospital_tasks_in_plan(df_enrich: pd.DataFrame, plan_df: pd.DataFrame) -> pd.DataFrame:
    """Liste des tâches (tronçons) à réparer pour tous les autres bâtiments dans l'ordre du plan glouton."""
    # bâtiments sélectionnés par le plan (hors hôpital)
    plan_order = plan_df["id_batiment"].tolist()
    non_hosp = df_enrich[df_enrich["is_hospital"] != 1]
    non_hosp = non_hosp[non_hosp["a_reparer"] == 1]
    # on conserve l'ordre des bâtiments du plan
    non_hosp["__ord"] = non_hosp["id_batiment"].apply(lambda b: plan_order.index(b) if b in plan_order else 10**9)
    non_hosp = non_hosp.sort_values(["__ord", "cost_total", "time_total_h"], ascending=[True, False, False]).drop(columns="__ord")
    return non_hosp.reset_index(drop=True)


def _assign_phases_by_cost_cum(df_tasks: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Découpe en phases par paliers de coût cumulé :
      - Phase 0 : hôpital (marqué is_hospital=1)
      - Phase 1 : jusqu'à 40% du coût total (hors phase 0)
      - Phases 2, 3, 4 : trois paliers ~20% chacun
    """
    df = df_tasks.copy()

    # Phase 0: déjà marquée (is_hospital==1)
    df["phase"] = np.where(df["is_hospital"] == 1, 0, np.nan)

    # Sépare hôpital / non-hôpital pour le découpage
    hosp_cost = df.loc[df["is_hospital"] == 1, "cost_total"].sum()
    rest = df[df["is_hospital"] != 1].copy()

    total_cost_all = df["cost_total"].sum()
    total_cost_rest = rest["cost_total"].sum()

    if total_cost_rest <= 0:
        # Tout est phase 0
        df["phase"] = 0
        summary = (
            df.groupby("phase", dropna=False)
              .agg(cost_phase=("cost_total","sum"), time_phase_h=("time_total_h","sum"))
              .reset_index()
        )
        return df, summary

    # cumul coût sur le reste
    rest = rest.sort_values(["plan_order", "cost_total", "time_total_h"], ascending=[True, False, False]).reset_index(drop=True)
    rest["cost_cum"] = rest["cost_total"].cumsum()
    rest["pct_cum_rest"] = rest["cost_cum"] / total_cost_rest

    # seuils : 40%, 60%, 80%, 100% du "reste"
    cut1, cut2, cut3 = 0.40, 0.60, 0.80

    def bucket(p):
        if p <= cut1: return 1
        if p <= cut2: return 2
        if p <= cut3: return 3
        return 4

    rest["phase"] = rest["pct_cum_rest"].apply(bucket)

    # réassemble
    keep_cols = ["phase"]
    df.loc[rest.index, keep_cols] = rest[keep_cols]

    # calculs cumulatifs globaux
    df = df.sort_values(["phase", "plan_order", "is_hospital"], ascending=[True, True, False]).reset_index(drop=True)
    df["cost_cum"] = df["cost_total"].cumsum()
    df["time_cum_h"] = df["time_total_h"].cumsum()
    df["pct_cum_all"] = df["cost_cum"] / max(total_cost_all, 1e-9)

    # synthèse
    summary = (
        df.groupby("phase", dropna=False)
          .agg(cost_phase=("cost_total","sum"),
               time_phase_h=("time_total_h","sum"))
          .reset_index()
          .sort_values("phase")
    )
    return df, summary


def build_work_orders(
    df_enrich: pd.DataFrame,
    plan_df: pd.DataFrame,
    costs_yaml: str | Path,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Construit un tableau d'ordres de travaux par tronçon (infra) :
      - Hôpital d'abord
      - Puis les autres dans l'ordre du plan glouton
      - Découpage en phases coût (40 / 20 / 20 / 20)
      - Ajoute cumul coût/temps
    Retourne (work_orders, phases_summary, meta)
    """
    cfg = _load_cfg(costs_yaml)
    gen_h = float(cfg["hospital"]["generator_hours"])
    margin = float(cfg["hospital"]["time_margin"])
    hosp_goal = gen_h * (1.0 - margin)  # ex: 20h * (1-0.2)=16h

    # 1) tâches hôpital
    hosp_tasks = _collect_hospital_tasks(df_enrich)
    hosp_tasks = hosp_tasks.assign(plan_order=0)  # toujours en tête

    # 2) tâches non-hôpital dans l'ordre du plan
    non_hosp_tasks = _collect_non_hospital_tasks_in_plan(df_enrich, plan_df)
    # L'ordre de plan : rang du bâtiment
    order_map = {bid: i for i, bid in enumerate(plan_df["id_batiment"].tolist(), start=1)}
    non_hosp_tasks["plan_order"] = non_hosp_tasks["id_batiment"].map(order_map).fillna(10**9).astype(int)

    # 3) concat
    tasks = pd.concat([hosp_tasks, non_hosp_tasks], ignore_index=True, sort=False)

    # 4) colonnes minimales pour export planning
    cols = [
        "id_batiment", "is_hospital", "infra_id", "type_infra",
        "longueur", "man_hours", "time_total_h",
        "material_cost", "labor_cost", "cost_total",
        "plan_order"
    ]
    for c in cols:
        if c not in tasks.columns:
            tasks[c] = np.nan

    tasks = tasks[cols].copy()

    # 5) assignation de phases + cumuls
    work_orders, phases_summary = _assign_phases_by_cost_cum(tasks)

    # 6) contrôle marge hôpital (somme des temps des tronçons hôpital)
    hosp_time_needed = work_orders.loc[work_orders["is_hospital"] == 1, "time_total_h"].sum()
    hospital_ok = (hosp_time_needed <= hosp_goal + 1e-9)

    meta = {
        "hospital_time_needed_h": float(hosp_time_needed),
        "hospital_time_goal_h": float(hosp_goal),
        "hospital_margin_ok": bool(hospital_ok),
    }
    return work_orders, phases_summary, meta
