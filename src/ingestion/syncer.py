import pandas as pd

class Syncer:
    """reseau_sync = reseau_arbre corrigé/enrichi : nb_maisons + type_batiment + type_infra."""
    @staticmethod
    def reseau_sync(df_arbre: pd.DataFrame, df_bat: pd.DataFrame, df_infra: pd.DataFrame) -> pd.DataFrame:
        base = df_arbre.drop(columns=["nb_maisons"], errors="ignore")
        out = (
            base.merge(df_bat[["id_batiment","nb_maisons","type_batiment"]],
                       on="id_batiment", how="left", validate="many_to_one")
                .merge(df_infra[["id_infra","type_infra"]],
                       left_on="infra_id", right_on="id_infra", how="left", validate="many_to_one")
                .drop(columns=["id_infra"])
        )
        return out
