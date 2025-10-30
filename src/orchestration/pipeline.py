import pandas as pd
import geopandas as gpd
import os

from src.ingestion.readers import DataReaders
from src.ingestion.cleaner import Cleaner
from src.ingestion.syncer import Syncer
from src.analytics.baselines import Baselines
from src.viz.lines import LinesViz
from src.exports.writers import Writers

class ElectricNetworkPipeline:
    """Pipeline mince : n'orchestrer que les appels pour garder le code modulaire et lisible."""

    def __init__(self, settings: dict):
        self.s = settings
        self.w = Writers(settings.get("staging_dir","data/staging"),
                         settings.get("outputs_dir","data/outputs"))

        # state
        self.df_bat = self.df_infra = self.df_arbre = None
        self.df_sync = self.df_infra_agg = self.df_bat_agg = None
        self.gdf_bat = self.gdf_infra = self.gdf_lines = None
        self.kpi = {}
        self.notes = {}
        self.map = None
        self.manifest = {}

    def __repr__(self):
        return f"<ENetPipe bat={0 if self.df_bat is None else len(self.df_bat)} infra={0 if self.df_infra is None else len(self.df_infra)} reseau={0 if self.df_arbre is None else len(self.df_arbre)}>"

    def run(self):
        self.load()
        self.prepare()
        self.analyze()
        self.visualize()
        self.export()
        return self

    # --- étapes ---
    def load(self):
        r = DataReaders()
        p = self.s["inputs"]
        self.df_bat   = r.read_batiments(p["batiments"])
        self.df_infra = r.read_infra(p["infra"])
        self.df_arbre = r.read_reseau_arbre(p["reseau_arbre"], self.s.get("sheet_name","reseau_en_arbre"))

        # shapefiles (optionnels)
        self.gdf_bat   = r.read_shp(p.get("batiments_shp",""))
        self.gdf_infra = r.read_shp(p.get("infrastructures_shp",""))

    def prepare(self):
        # nettoyage soft + typage
        self.df_bat   = Cleaner.to_numeric(Cleaner.strip(self.df_bat),   ["nb_maisons"])
        self.df_infra = Cleaner.strip(self.df_infra)
        self.df_arbre = Cleaner.to_numeric(Cleaner.strip(self.df_arbre), ["nb_maisons","longueur"])
        # filtres/QA
        self.df_arbre, n_len = Cleaner.drop_len_anomalies(self.df_arbre, "longueur", 0.0)
        self.df_arbre, n_dup = Cleaner.drop_pair_dupes(self.df_arbre, ("id_batiment","infra_id"))
        self.notes.update({"longueur<=0_supprimees": n_len, "dup_pairs_supprimes": n_dup})
        # jointures minimales
        self.df_sync = Syncer.reseau_sync(self.df_arbre, self.df_bat, self.df_infra)

    def analyze(self):
        self.df_infra_agg = Baselines.agg_infra(self.df_sync)
        self.df_bat_agg   = Baselines.agg_bat(self.df_sync)
        self.kpi          = Baselines.kpi(self.df_sync, self.df_bat, self.df_infra, self.notes)

    def visualize(self):
        self.gdf_lines = LinesViz.enrich_lines(self.gdf_infra, self.df_infra_agg) if self.gdf_infra is not None else None
        self.map = LinesViz.folium_map(self.gdf_lines, self.gdf_bat) if self.gdf_lines is not None else None

    def export(self):
        # staging
        p_sync = self.w.csv(self.df_sync,      self.w.staging_dir, "reseau_sync")
        p_iagg = self.w.csv(self.df_infra_agg, self.w.staging_dir, "infra_agg_baseline")
        p_bagg = self.w.csv(self.df_bat_agg,   self.w.staging_dir, "bat_agg_baseline")
        p_kpi  = self.w.json(self.kpi,         self.w.staging_dir, "kpi_baseline")
        # segments à réparer vs OK
        seg = self.df_infra_agg[["infra_id","type_infra","infra_type_logique","bat_desservis","prises_total","longueur_ref"]].copy()
        seg_bad = seg[seg["infra_type_logique"].str.lower()=="a_remplacer"]
        seg_ok  = seg[seg["infra_type_logique"].str.lower()!="a_remplacer"]
        p_bad = self.w.csv(seg_bad, self.w.outputs_dir, "segments_a_reparer")
        p_ok  = self.w.csv(seg_ok,  self.w.outputs_dir, "segments_ok")
        # geojson (si couche enrichie)
        p_geo = self.w.geojson(self.gdf_lines, self.w.outputs_dir, "infrastructures_enrich")
        self.manifest = {
            "staging": {
                "reseau_sync": p_sync,
                "infra_agg_baseline": p_iagg,
                "bat_agg_baseline": p_bagg,
                "kpi_baseline": p_kpi
            },
            "outputs": {
                "segments_a_reparer": p_bad,
                "segments_ok": p_ok,
                "infrastructures_enrich_geojson": p_geo
            }
        }
