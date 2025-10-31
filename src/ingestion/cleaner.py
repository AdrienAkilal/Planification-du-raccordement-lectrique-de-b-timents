# src/ingestion/cleaner.py
from __future__ import annotations
import pandas as pd

# Colonnes attendues (on tolère plusieurs alias)
COLS_RESEAU = {
    "infra_id": ["infra_id", "id_infra", "infra"],
    "id_batiment": ["id_batiment", "bat_id", "id_bat", "building_id"],
    "longueur": ["longueur", "length", "len_m", "long_m"],
    "infra_type": ["infra_type", "type_infra", "type", "nature_infra", "categorie_infra", "infra_categorie"],
    # NEW: récupère aussi nb_maisons s'il existe dans l'XLSX réseau
    "nb_maisons": ["nb_maisons", "nb_foyers", "houses", "nb_houses", "nb_maison"],
}

COLS_BATS = {
    "id_batiment": ["id_batiment", "bat_id", "id_bat", "building_id"],
    "nb_maisons": ["nb_maisons", "nb_foyers", "maisons", "houses", "nb_houses", "nb_maison"],
    "type_batiment": ["type_batiment", "type", "categorie", "building_type"],
}

COLS_INFRA = {
    "infra_id": ["infra_id", "id_infra", "infra"],
    "type_infra": ["type_infra", "type", "nature_infra", "categorie_infra", "infra_categorie"],
}


def _coalesce(df: pd.DataFrame, mapping: dict[str, list[str]]) -> pd.DataFrame:
    """Crée les colonnes cibles en priorisant les alias si présents."""
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    for target, aliases in mapping.items():
        for a in aliases:
            if a in out.columns:
                out[target] = out[a]
                break
        if target not in out.columns:
            out[target] = pd.NA
    return out


def _normalize_type_infra(s):
    if pd.isna(s):
        return None
    s = str(s).strip().lower()
    m = {
        "aérien": "aerien", "aerien": "aerien",
        "semi-aérien": "semi-aerien", "semi aerien": "semi-aerien", "semi_aerien": "semi-aerien",
        "fourreau": "fourreau", "souterrain": "fourreau", "underground": "fourreau",
        # tolérances fréquentes
        "aerien ": "aerien", " aérien": "aerien",
        "semi–aérien": "semi-aerien", "semi-aerien ": "semi-aerien",
        "fourreaux": "fourreau",
    }
    return m.get(s, s)


def clean_and_join(
    df_reseau: pd.DataFrame,
    df_bat: pd.DataFrame | None,
    df_infra: pd.DataFrame | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Normalise schémas + jointure:
    - df (réseau enrichi): [infra_id, id_batiment, longueur, type_infra, ...]
    - infra_base (agrégats par infra)
    - bat_base (caractéristiques uniques batiments)
    """
    df_reseau = _coalesce(df_reseau, COLS_RESEAU)
    if df_bat is not None:
        df_bat = _coalesce(df_bat, COLS_BATS)
    else:
        df_bat = pd.DataFrame(columns=list(COLS_BATS.keys()))

    if df_infra is not None:
        df_infra = _coalesce(df_infra, COLS_INFRA)
    else:
        df_infra = pd.DataFrame(columns=list(COLS_INFRA.keys()))

    # Normalisations de base
    df_reseau["infra_id"] = df_reseau["infra_id"].astype(str)
    df_reseau["id_batiment"] = df_reseau["id_batiment"].astype(str)
    df_reseau["longueur"] = pd.to_numeric(df_reseau["longueur"], errors="coerce").fillna(0.0)

    # nb_maisons côté réseau si présent → numeric propre
    if "nb_maisons" in df_reseau.columns:
        df_reseau["nb_maisons"] = (
            pd.to_numeric(df_reseau["nb_maisons"], errors="coerce")
              .fillna(1).clip(lower=0).astype(int)
        )

    # Source type depuis infra si besoin
    type_src = None
    if "type_infra" in df_infra.columns:
        type_src = "type_infra"
    for alt in ["type", "nature_infra", "categorie_infra", "infra_categorie"]:
        if alt in df_infra.columns and type_src is None:
            type_src = alt
    if type_src:
        df_infra["type_infra_src"] = df_infra[type_src]
    else:
        df_infra["type_infra_src"] = pd.NA

    # Joins
    df = df_reseau.merge(df_infra[["infra_id", "type_infra_src"]], on="infra_id", how="left")
    df = df.merge(df_bat[["id_batiment", "nb_maisons", "type_batiment"]], on="id_batiment", how="left")

    # Final type_infra: priorité input réseau, sinon source infra
    a = df.get("infra_type")  # alias éventuel de l'xlsx
    b = df.get("type_infra")  # alias éventuel déjà coalescé
    c = df.get("type_infra_src")
    tmp = a if a is not None else b
    df["type_infra"] = tmp.where(tmp.notna(), c)
    df["type_infra"] = df["type_infra"].map(_normalize_type_infra)

    # >>> Fallback robuste pour nb_maisons <<<
    # 1) si nb_maisons manquant après merge, on prend celui du réseau (groupby) si dispo
    if "nb_maisons" not in df.columns or df["nb_maisons"].isna().all():
        if "nb_maisons" in df_reseau.columns:
            # max par bâtiment (ou sum, selon ta logique métier)
            nb_from_reseau = (df_reseau.groupby("id_batiment", dropna=False)["nb_maisons"]
                                        .max().rename("nb_maisons"))
            df = df.drop(columns=[c for c in ["nb_maisons"] if c in df.columns], errors="ignore") \
                   .merge(nb_from_reseau, on="id_batiment", how="left")
        else:
            df["nb_maisons"] = pd.NA

    # 2) valeurs sûres
    df["nb_maisons"] = (
        pd.to_numeric(df["nb_maisons"], errors="coerce")
          .fillna(1).clip(lower=0).astype(int)
    )

    # Bases uniques
    infra_base = (
        df.groupby(["infra_id", "type_infra"], dropna=False)
          .agg(longueur=("longueur", "sum"))
          .reset_index()
    )

    bat_base = (
        df.groupby(["id_batiment"], dropna=False)
          .agg(nb_maisons=("nb_maisons", "max"),
               type_batiment=("type_batiment", "first"))
          .reset_index()
    )

    return df, infra_base, bat_base
