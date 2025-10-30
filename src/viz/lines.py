import geopandas as gpd
import folium
from typing import Optional

class LinesViz:
    @staticmethod
    def enrich_lines(gdf_infra: gpd.GeoDataFrame, infra_agg) -> Optional[gpd.GeoDataFrame]:
        if gdf_infra is None: return None
        try:
            if gdf_infra.crs and gdf_infra.crs.to_epsg() != 4326:
                gdf_infra = gdf_infra.to_crs(4326)
        except Exception:
            pass
        cols = ["infra_id","type_infra","infra_type_logique","bat_desservis","prises_total","longueur_ref"]
        return gdf_infra.merge(infra_agg[cols], on="infra_id", how="left", validate="one_to_one")

    @staticmethod
    def folium_map(gdf_lines: gpd.GeoDataFrame, gdf_points: Optional[gpd.GeoDataFrame]=None) -> Optional[folium.Map]:
        if gdf_lines is None or gdf_lines.empty: return None
        try:
            center = [float(gdf_lines.geometry.centroid.y.mean()), float(gdf_lines.geometry.centroid.x.mean())]
        except Exception:
            center = [0,0]
        m = folium.Map(location=center, zoom_start=13, tiles="CartoDB positron")
        def style(feat):
            p = feat["properties"]
            base = {"aerien":"#1f77b4","semi-aerien":"#ff7f0e","fourreau":"#2ca02c"}.get((p.get("type_infra") or "").lower(), "#888")
            bad = (str(p.get("infra_type_logique","")).lower() == "a_remplacer")
            return {"color":"#d62728" if bad else base, "weight":3 if bad else 2, "opacity":0.95}
        folium.GeoJson(
            gdf_lines.to_json(),
            name="Infras",
            style_function=style,
            tooltip=folium.GeoJsonTooltip(
                fields=["infra_id","type_infra","infra_type_logique","bat_desservis","prises_total","longueur_ref"],
                aliases=["Infra","Nature","Statut","Bât. desservis","Prises tot.","Longueur (m)"]
            )
        ).add_to(m)
        if gdf_points is not None and not gdf_points.empty:
            try:
                if gdf_points.crs and gdf_points.crs.to_epsg() != 4326:
                    gdf_points = gdf_points.to_crs(4326)
            except Exception:
                pass
            for _, r in gdf_points.iterrows():
                folium.CircleMarker([r.geometry.y, r.geometry.x], radius=3, color="#6366F1",
                                    fill=True, fill_opacity=0.9,
                                    popup=str(r.get("id_batiment",""))).add_to(m)
        folium.LayerControl().add_to(m)
        return m
