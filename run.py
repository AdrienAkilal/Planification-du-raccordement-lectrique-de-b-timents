# run.py
from src.orchestration.pipeline import ElectricNetworkPipeline

paths = {
    "reseau_en_arbre": "data/inputs/reseau_en_arbre.xlsx",  # XLSX
    "batiments":       "data/inputs/batiments.csv",
    "infra":           "data/inputs/infra.csv",
    # optionnels
    # "travaux":      "data/inputs/travaux.csv",
    "costs_yaml":      "configs/costs.yaml",
}

if __name__ == "__main__":
    p = ElectricNetworkPipeline(paths)
    result = p.run()
    print("=== Pipeline terminé ===")
    print(result)
