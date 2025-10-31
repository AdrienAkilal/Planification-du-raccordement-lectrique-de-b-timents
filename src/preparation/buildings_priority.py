import pandas as pd

CAT_MAP = {"hôpital":"hopital","hopital":"hopital","école":"ecole","ecole":"ecole","habitation":"habitation"}
CAT_SCORE = {"hopital":0.0, "ecole":0.5, "habitation":1.0}

def add_building_priority(df_bat_base: pd.DataFrame) -> pd.DataFrame:
    df = df_bat_base.copy()
    norm = df["type_batiment"].fillna("habitation").str.strip().str.lower().map(CAT_MAP).fillna("habitation")
    df["type_batiment_norm"] = norm
    df["cat_score"] = df["type_batiment_norm"].map(CAT_SCORE).fillna(1.0)
    # occupation par défaut = 1.0 (pas d’info)
    df["occ_rate"] = 1.0
    df["is_uninhabited"] = (df["occ_rate"] <= 0.0).astype(int)

    # sanity: un seul hôpital
    n_hosp = (df["type_batiment_norm"]=="hopital").sum()
    if n_hosp != 1:
        print(f"⚠️  Alerte cohérence: hôpitaux détectés = {n_hosp} (attendu = 1).")

    return df
