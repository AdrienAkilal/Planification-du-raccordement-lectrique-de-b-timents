# src/orchestration/pipeline.py
from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.utils.paths import staging_dir, outputs_dir
from src.ingestion.readers import read_table, read_csv
from src.ingestion.cleaner import clean_and_join
from src.ingestion.syncer import apply_business_csv
from src.preparation.buildings_priority import add_building_priority
from src.preparation.enrichments import enrich_costs_and_flags
from src.analytics.baselines import compute_kpis, save_kpis
from src.analytics.plan_greedy import greedy_plan
from src.exports.writers import save_csv
from src.analytics.work_organizer import build_work_orders


class ElectricNetworkPipeline:
    """
    Orchestrateur minimal :
      - lit les fichiers d'entrée (xlsx + csv)
      - appelle les modules (clean/join, sync métier, enrich, kpi, plan)
      - dépose les fichiers en staging/ et outputs/
    """

    def __init__(self, paths: dict, crs_metric: str = "EPSG:2154"):
        """
        paths attend au minimum :
          paths = {
            "reseau_en_arbre": "data/inputs/reseau_en_arbre.xlsx",
            "batiments":       "data/inputs/batiments.csv",
            "infra":           "data/inputs/infra.csv",
            # optionnels :
            "travaux":         "data/inputs/travaux.csv",
            "costs_yaml":      "configs/costs.yaml",
          }
        """
        self.paths = paths
        self.crs = crs_metric
        self.staged: dict[str, str] = {}
        self.outputs: dict[str, str] = {}

    # ------------------------------
    # Helpers
    # ------------------------------
    def _read_inputs(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None, pd.DataFrame | None]:
        # Reseau (XLSX) + Batiments/Infra (CSV)
        df_reseau = read_table(self.paths["reseau_en_arbre"])           # xlsx
        df_bat    = read_csv(self.paths["batiments"])                    # csv
        df_infra  = read_csv(self.paths["infra"])                        # csv
        df_trav   = read_csv(self.paths["travaux"]) if self.paths.get("travaux") else None

        # Normalisation légère des en-têtes
        for df in (df_reseau, df_bat, df_infra):
            df.columns = [c.strip().lower() for c in df.columns]

        # Trace utile
        print(f"[INGEST] reseau:{df_reseau.shape} bat:{df_bat.shape} infra:{df_infra.shape} trav:{None if df_trav is None else df_trav.shape}")

        return df_reseau, df_bat, df_infra, df_trav

    def _stage_exports(self, df_sync: pd.DataFrame, infra_base: pd.DataFrame,
                       bat_prio: pd.DataFrame, kpi_path: Path) -> None:
        sdir = staging_dir()
        self.staged["reseau_sync"]         = str(save_csv(df_sync,       sdir / "reseau_sync"))
        self.staged["infra_agg_baseline"]  = str(save_csv(infra_base,    sdir / "infra_agg_baseline"))
        self.staged["bat_agg_baseline"]    = str(save_csv(bat_prio,      sdir / "bat_agg_baseline"))
        self.staged["kpi_baseline"]        = str(kpi_path)

    # ------------------------------
    # Run
    # ------------------------------
    def run(self) -> dict:
        # 1) Read inputs (xlsx + csv)
        df_reseau, df_bat, df_infra, df_trav = self._read_inputs()

        # 2) Clean + join (aligne les colonnes, corrige nb_maisons via batiments, joint avec infra)
        df_joined, infra_base, bat_base = clean_and_join(df_reseau, df_bat, df_infra)

        # 3) Synchronisation métier (CSV "travaux & missions" : surclasse/complète les attributs)
        df_sync = apply_business_csv(df_joined, df_trav)

        # 4) Préparation (priorité bâtiment : ex. hôpital > école > habitation, + règles d’occupation si dispo)
        bat_prio = add_building_priority(bat_base)

        # 5) Enrichissement coûts/temps/flags (barèmes depuis costs.yaml si fourni)
        costs_yaml = self.paths.get("costs_yaml", "configs/costs.yaml")
        df_enrich = enrich_costs_and_flags(df_sync, costs_yaml)

        # 6) KPIs de base (répartition longueurs/coûts/temps par type d’infra)
        kpis = compute_kpis(df_enrich)
        kpi_path = save_kpis(kpis, staging_dir() / "kpi_baseline.json")

        # 7) Exports STAGING (datasets de référence pour audit)
        self._stage_exports(df_sync, infra_base, bat_prio, kpi_path)

        # 8) Segments à réparer / OK
        seg_ok  = df_enrich[df_enrich["a_reparer"] == 0].copy()
        seg_rep = df_enrich[df_enrich["a_reparer"] == 1].copy()
        odir = outputs_dir()
        self.outputs["segments_a_reparer"] = str(save_csv(seg_rep, odir / "segments_a_reparer"))
        self.outputs["segments_ok"]        = str(save_csv(seg_ok,  odir / "segments_ok"))

        # 9) Plan glouton
        plan_df = greedy_plan(df_enrich, bat_prio)
        self.outputs["plan_glouton"] = str(save_csv(plan_df, odir / "plan_glouton"))

        # 10) Organisation des travaux (Hôpital phase 0 + phases 40/20/20/20)
        work_orders, phases_summary, meta = build_work_orders(
            df_enrich=df_enrich,
            plan_df=plan_df,
            costs_yaml=costs_yaml
        )
        self.outputs["work_orders"]    = str(save_csv(work_orders,    odir / "work_orders"))
        self.outputs["phases_summary"] = str(save_csv(phases_summary, odir / "phases_summary"))

        if not meta["hospital_margin_ok"]:
            print(f"⚠️ HÔPITAL: {meta['hospital_time_needed_h']:.2f} h > objectif {meta['hospital_time_goal_h']:.2f} h (marge 20% NON respectée)")
        else:
            print(f"✅ HÔPITAL: {meta['hospital_time_needed_h']:.2f} h ≤ objectif {meta['hospital_time_goal_h']:.2f} h")

        return {"staging": self.staged, "outputs": self.outputs}
