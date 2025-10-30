from datetime import datetime
import os, json
import pandas as pd
import geopandas as gpd
from typing import Optional

class Writers:
    def __init__(self, staging_dir="data/staging", outputs_dir="data/outputs"):
        self.staging_dir, self.outputs_dir = staging_dir, outputs_dir
        os.makedirs(self.staging_dir, exist_ok=True)
        os.makedirs(self.outputs_dir, exist_ok=True)

    def _ts(self) -> str:
        return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

    def _vpath(self, base_dir: str, name: str, ext: str) -> str:
        return os.path.join(base_dir, f"{name}_{self._ts()}.{ext.lstrip('.')}")

    def csv(self, df: pd.DataFrame, base_dir: str, name: str) -> str:
        p = self._vpath(base_dir, name, "csv")
        df.to_csv(p, index=False)
        return p

    def json(self, obj: dict, base_dir: str, name: str) -> str:
        p = self._vpath(base_dir, name, "json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        return p

    def geojson(self, gdf: gpd.GeoDataFrame, base_dir: str, name: str) -> Optional[str]:
        if gdf is None or gdf.empty:
            return None
        p = self._vpath(base_dir, name, "geojson")
        gdf.to_file(p, driver="GeoJSON")
        return p
