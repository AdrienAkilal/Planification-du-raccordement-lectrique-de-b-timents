import pandas as pd

def apply_business_csv(df_reseau: pd.DataFrame, df_travaux: pd.DataFrame | None) -> pd.DataFrame:
    """
    Le CSV 'travaux & missions' peut forcer:
      - infra_type (état logique: 'infra_intacte' / 'a_reparer')
      - type_infra ('aerien'/'semi-aerien'/'fourreau')
      - fenêtres, coûts overrides, etc. (facultatif)
    """
    if df_travaux is None or df_travaux.empty:
        return df_reseau.copy()

    df_travaux = df_travaux.copy()
    for c in ("infra_id","infra_type","type_infra"):
        if c not in df_travaux: df_travaux[c] = None

    # on écrase/complète au niveau infra_id
    df = df_reseau.merge(df_travaux[["infra_id","infra_type","type_infra"]],
                         on="infra_id", how="left", suffixes=("","_csv"))

    df["infra_type"] = df["infra_type_csv"].fillna(df["infra_type"])
    df["type_infra"] = df["type_infra"].fillna(df["type_infra_csv"])
    df.drop(columns=[c for c in df.columns if c.endswith("_csv")], inplace=True)
    return df
