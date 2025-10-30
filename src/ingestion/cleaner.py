import pandas as pd
from typing import Tuple, List

class Cleaner:
    @staticmethod
    def strip(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = df.columns.str.strip()
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = df[c].str.strip()
        return df

    @staticmethod
    def to_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
        df = df.copy()
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    @staticmethod
    def drop_len_anomalies(df: pd.DataFrame, col="longueur", min_val=0.0) -> Tuple[pd.DataFrame, int]:
        if col not in df.columns:
            return df, 0
        bad = df[col] <= min_val
        n = int(bad.sum())
        return df.loc[~bad].copy(), n

    @staticmethod
    def drop_pair_dupes(df: pd.DataFrame, subset=("id_batiment","infra_id")) -> Tuple[pd.DataFrame, int]:
        before = len(df)
        df2 = df.drop_duplicates(list(subset))
        return df2, int(before - len(df2))
