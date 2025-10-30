import pandas as pd
from typing import Dict, Any

class Baselines:
    @staticmethod
    def agg_infra(df_sync: pd.DataFrame) -> pd.DataFrame:
        # statut logique par infra : un seul segment 'a_remplacer' suffit pour marquer l'infra entière
        mapping = {"infra_intacte":0, "a_remplacer":1}
        mx = (df_sync.assign(_s=df_sync["infra_type"].map(mapping))
                    .groupby("infra_id")["_s"].max())
        rev = {0:"infra_intacte", 1:"a_remplacer"}
        agg = (df_sync.groupby(["infra_id","type_infra"], as_index=False)
                      .agg(bat_desservis=("id_batiment","nunique"),
                           prises_total=("nb_maisons","sum"),
                           longueur_ref=("longueur","mean")))
        agg["infra_type_logique"] = mx.reindex(agg["infra_id"]).map(rev).values
        return agg

    @staticmethod
    def agg_bat(df_sync: pd.DataFrame) -> pd.DataFrame:
        return (df_sync.groupby(["id_batiment","type_batiment"], as_index=False)
                       .agg(prises=("nb_maisons","first"),
                            longueur_totale=("longueur","sum"),
                            n_infras=("infra_id","nunique")))

    @staticmethod
    def kpi(df_sync: pd.DataFrame, df_bat: pd.DataFrame, df_infra: pd.DataFrame, notes: dict) -> Dict[str, Any]:
        return {
            "n_batiments": int(df_bat["id_batiment"].nunique()),
            "n_infras": int(df_infra["id_infra"].nunique()),
            "n_lignes_reseau_sync": int(len(df_sync)),
            "infra_type_logique": df_sync["infra_type"].value_counts(dropna=False).to_dict(),
            "type_infra": df_sync["type_infra"].value_counts(dropna=False).to_dict(),
            "longueur_desc": df_sync["longueur"].describe().to_dict(),
            "notes_nettoyage": notes
        }
