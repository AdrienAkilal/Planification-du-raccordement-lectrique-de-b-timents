from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import pandas as pd


# ------------------------
# Modèle Infra & Batiment
# ------------------------

@dataclass
class Infra:
    infra_id: str
    length: float
    infra_type_state: str   # 'infra_intacte' ou autre
    nb_houses: int = 0      # maisons raccordées via cette infra (mutualisation)
    repaired: bool = False

    def repair_infra(self) -> None:
        # on aligne l'état logique et sémantique
        self.repaired = True
        self.infra_type_state = "infra_intacte"

    def get_infra_difficulty(self) -> float:
        # Difficulté(infra) = longueur / nb_maisons (min 1)
        denom = max(1, int(self.nb_houses))
        return float(self.length) / float(denom)

    def __radd__(self, other: float) -> float:
        # autorise sum([infra1, infra2, ...]) si on veut
        return (other or 0.0) + self.get_infra_difficulty()


@dataclass
class Batiment:
    id_building: str
    nb_houses: int
    type_batiment: str = "habitation"
    list_infras: List[Infra] = field(default_factory=list)

    def get_building_difficulty(self) -> float:
        # Difficulté(bâtiment) = somme difficultés des infras non réparées
        return float(sum(i.get_infra_difficulty() for i in self.list_infras
                         if not i.repaired and i.infra_type_state != "infra_intacte"))

    # tri “naturel” : difficulté croissante puis id pour la stabilité
    def __lt__(self, other: "Batiment") -> bool:
        d1, d2 = self.get_building_difficulty(), other.get_building_difficulty()
        if d1 != d2:
            return d1 < d2
        return self.id_building < other.id_building


# ------------------------
# Construction du graphe
# ------------------------

def build_graph(df_sync: pd.DataFrame,
                df_bat_base: pd.DataFrame) -> Tuple[Dict[str, Infra], Dict[str, Batiment]]:
    """
    df_sync : colonnes attendues -> ['infra_id','id_batiment','longueur','infra_type','nb_maisons']
    df_bat_base : ['id_batiment','nb_maisons','type_batiment']
    """
    # mutualisation: nb maisons desservies par chaque infra
    nb_by_infra = (df_sync.groupby("infra_id", dropna=False)["nb_maisons"]
                        .sum().rename("nb_houses").reset_index())

    infras: Dict[str, Infra] = {}
    for _, row in (df_sync.merge(nb_by_infra, on="infra_id", how="left")).iterrows():
        iid = str(row["infra_id"])
        if iid not in infras:
            infras[iid] = Infra(
                infra_id=iid,
                length=float(row["longueur"]),
                infra_type_state=str(row["infra_type"]).lower(),
                nb_houses=int(row["nb_houses"] or 0),
            )

    # bâtiments (on prend le type_batiment depuis la base)
    bats: Dict[str, Batiment] = {}
    for _, row in df_bat_base.iterrows():
        bid = str(row["id_batiment"])
        bats[bid] = Batiment(
            id_building=bid,
            nb_houses=int(row["nb_maisons"]),
            type_batiment=str(row.get("type_batiment", "habitation")),
        )

    # liaisons bâtiment → infras
    for _, row in df_sync.iterrows():
        bats[str(row["id_batiment"])].list_infras.append(infras[str(row["infra_id"])])

    return infras, bats


def phase0_buildings(bats: Dict[str, Batiment]) -> List[str]:
    """Bâtiments dont toutes les infras sont déjà intactes => phase 0."""
    out: List[str] = []
    for b in bats.values():
        if all(i.infra_type_state == "infra_intacte" for i in b.list_infras):
            out.append(b.id_building)
    return out


# ------------------------
# Algo glouton demandé
# ------------------------

def greedy_plan(df_sync: pd.DataFrame,
                df_bat_base: pd.DataFrame) -> pd.DataFrame:
    """
    Mission:
      - prioriser les bâtiments les plus simples (difficulté min),
      - maximiser implicitement les prises via la mutualisation,
      - réparer toutes les infras du bâtiment choisi à chaque itération.

    Renvoie un DataFrame des étapes avec:
      step, id_batiment, type_batiment, nb_houses,
      building_difficulty_before, repaired_infras
    """
    infras, bats = build_graph(df_sync, df_bat_base)

    # phase 0 (zéro réparation)
    phase0 = phase0_buildings(bats)

    # liste des batis qui nécessitent au moins 1 réparation
    impacted = [b for b in bats.values()
                if any(i.infra_type_state != "infra_intacte" for i in b.list_infras)]

    plan_rows: List[dict] = []
    step = 0

    # insérer les phase 0 (étape 0)
    for bid in sorted(phase0):
        b = bats[bid]
        plan_rows.append({
            "step": 0,
            "id_batiment": b.id_building,
            "type_batiment": b.type_batiment,
            "nb_houses": b.nb_houses,
            "building_difficulty_before": 0.0,
            "repaired_infras": [],
        })

    # boucle tant qu’il reste des bâtiments impactés
    while impacted:
        impacted.sort()                     # __lt__ sur difficulté puis id
        choix = impacted.pop(0)             # le moins difficile
        step += 1

        # *** IMPORTANT : difficulté AVANT réparation ***
        diff_before = choix.get_building_difficulty()

        # réparer toutes ses infras non intactes/non réparées
        repaired_ids: List[str] = []
        for i in choix.list_infras:
            if not i.repaired and i.infra_type_state != "infra_intacte":
                i.repair_infra()
                repaired_ids.append(i.infra_id)

        plan_rows.append({
            "step": step,
            "id_batiment": choix.id_building,
            "type_batiment": choix.type_batiment,
            "nb_houses": choix.nb_houses,
            "building_difficulty_before": diff_before,
            "repaired_infras": repaired_ids,
        })

        # filtrer ceux qui ont encore au moins 1 infra à réparer
        impacted = [b for b in impacted
                    if any((not i.repaired) and i.infra_type_state != "infra_intacte"
                           for i in b.list_infras)]

    return pd.DataFrame(plan_rows)
