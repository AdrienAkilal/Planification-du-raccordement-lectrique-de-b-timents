import geopandas as gpd
from pathlib import Path

def export_lines_geojson(df_enrich, crs: str, out_path: str | Path):
    gdf = gpd.GeoDataFrame(df_enrich.copy(), geometry="geometry", crs=crs)
    p = Path(out_path); p.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(p, driver="GeoJSON")
    return p
