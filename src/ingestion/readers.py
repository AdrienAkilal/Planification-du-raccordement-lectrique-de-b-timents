import os
import pandas as pd
import geopandas as gpd
from typing import Optional

class DataReaders:
    def read_batiments(self, path: str) -> pd.DataFrame:
        return pd.read_csv(path, dtype=str)

    def read_infra(self, path: str) -> pd.DataFrame:
        return pd.read_csv(path, dtype=str)

    def read_reseau_arbre(self, path: str, sheet: str = "reseau_en_arbre") -> pd.DataFrame:
        return pd.read_excel(path, sheet_name=sheet, dtype=str)

    def read_shp(self, path: str) -> Optional[gpd.GeoDataFrame]:
        return gpd.read_file(path) if path and os.path.exists(path) else None
