from src.orchestration.pipeline import ElectricNetworkPipeline

settings = {
    "inputs": {
        "batiments": r"data/inputs/batiments.csv",
        "infra": r"data/inputs/infra.csv",
        "reseau_arbre": r"data/inputs/reseau_en_arbre.xlsx",
        "batiments_shp": r"data/inputs/batiments.shp",
        "infrastructures_shp": r"data/inputs/infrastructures.shp"
    },
    "sheet_name": "reseau_en_arbre",
    "staging_dir": r"data/staging",
    "outputs_dir": r"data/outputs"
}

if __name__ == "__main__":
    pipe = ElectricNetworkPipeline(settings).run()

    print("=== Pipeline terminée ===")
    print(pipe.manifest)
    if pipe.gdf_infra is not None:
        print("CRS:", pipe.gdf_infra.crs)
