# 🔌 Guide d'utilisation - Planification du raccordement électrique

## ✅ Problèmes identifiés et corrigés

### 1. **Imports dupliqués** dans `pipeline.py`
- ❌ Problème : `from src.utils.paths import staging_dir` importé 2 fois
- ✅ Correction : Import unique et commentaires nettoyés

### 2. **Code dupliqué** dans `pipeline.py`
- ❌ Problème : Appel de `greedy_plan()` et `save_csv()` dupliqué en fin de fichier
- ✅ Correction : Code dupliqué supprimé

### 3. **Dépendances manquantes**
- ❌ Problème : Module `yaml` non installé
- ✅ Correction : Fichier `requirements.txt` créé avec toutes les dépendances

### 4. **Configuration YAML incompatible**
- ❌ Problème : Structure YAML (`units`, `workforce`) différente du code
- ✅ Correction : Code adapté pour supporter la structure YAML du fichier `costs.yaml`

### 5. **Colonne `is_hospital` manquante**
- ❌ Problème : `work_organizer.py` cherche une colonne inexistante
- ✅ Correction : Ajout de la détection automatique des hôpitaux dans `enrichments.py`

### 6. **Avertissement type_infra inconnus**
- ⚠️ Observation : Les valeurs `infra_intacte` et `a_remplacer` dans la colonne `infra_type` ne sont pas reconnues comme types d'infrastructure
- 💡 Note : C'est normal, ces valeurs représentent l'état, pas le type (aérien/fourreau/etc.)

---

## 🚀 Comment exécuter le projet

### 1️⃣ **Installation des dépendances**

```powershell
# Installer les packages Python requis
pip install -r requirements.txt
```

ou manuellement :
```powershell
pip install pandas openpyxl pyyaml
```

### 2️⃣ **Préparer les fichiers d'entrée**

Vérifier que ces fichiers existent dans `data/inputs/` :
- ✅ `reseau_en_arbre.xlsx` - Réseau électrique en arbre
- ✅ `batiments.csv` - Métadonnées des bâtiments
- ✅ `infra.csv` - Métadonnées des infrastructures
- (optionnel) `travaux.csv` - Données métier additionnelles

### 3️⃣ **Exécution**

```powershell
# Depuis la racine du projet
python run.py
```

### 4️⃣ **Résultats**

Les fichiers générés se trouvent dans :

#### 📁 `data/staging/` (fichiers intermédiaires)
- `reseau_sync_<timestamp>.csv` - Réseau synchronisé
- `infra_agg_baseline_<timestamp>.csv` - Agrégats infrastructures
- `bat_agg_baseline_<timestamp>.csv` - Agrégats bâtiments avec priorités
- `kpi_baseline.json` - Indicateurs de performance

#### 📁 `data/outputs/` (résultats finaux)
- `segments_ok_<timestamp>.csv` - Segments déjà en bon état
- `segments_a_reparer_<timestamp>.csv` - Segments nécessitant réparation
- `plan_glouton_<timestamp>.csv` - **Plan de raccordement optimisé** 🎯
- `work_orders_<timestamp>.csv` - Ordres de travaux détaillés
- `phases_summary_<timestamp>.csv` - Résumé par phase

---

## 📊 Algorithme de planification

### Principe : **Glouton par difficulté minimale**

```
Difficulté(infrastructure) = longueur / nb_maisons
Difficulté(bâtiment) = Σ difficulté(infras non réparées)
```

### Étapes :
1. **Phase 0** : Bâtiments déjà raccordés (toutes infras intactes)
2. **Tri** : Par difficulté croissante → les plus simples d'abord
3. **Itération** : Choisir le bâtiment le moins difficile
4. **Réparation** : Marquer toutes ses infrastructures comme réparées
5. **Répéter** jusqu'à épuisement

### Avantages :
✅ Simple et transparent (facile à expliquer en soutenance)
✅ Maximise implicitement les prises (mutualisation)
✅ Priorise l'efficacité (longueur/maisons)

---

## 🏥 Gestion des hôpitaux

Le système détecte automatiquement les bâtiments de type "hôpital" et les traite en **priorité absolue** :
- Phase 0 réservée aux hôpitaux
- Objectif : raccordement en ≤ 16h (marge 20% sur autonomie 20h)

---

## 🔧 Structure du projet

```
Planification-du-raccordement-électrique-de-bâtiments/
├── run.py                    # Point d'entrée principal
├── requirements.txt          # Dépendances Python
├── configs/
│   └── costs.yaml           # Barèmes coûts/temps
├── data/
│   ├── inputs/              # Données sources
│   ├── staging/             # Fichiers intermédiaires
│   └── outputs/             # Résultats finaux
└── src/
    ├── ingestion/           # Lecture et nettoyage
    ├── preparation/         # Enrichissements
    ├── analytics/           # Algorithmes (plan glouton)
    ├── exports/             # Sauvegarde CSV
    ├── orchestration/       # Pipeline principal
    └── utils/               # Utilitaires
```

---

## 💡 Conseils pour la soutenance

### Points forts à mettre en avant :
1. **Architecture modulaire** → maintenable et extensible
2. **Algorithme transparent** → facile à expliquer et justifier
3. **Mutualisation automatique** → optimise le coût par prise
4. **Gestion des priorités** → hôpitaux en phase 0
5. **Traçabilité complète** → tous les fichiers intermédiaires conservés

### Métriques clés à présenter :
- Nombre de bâtiments raccordés par phase
- Coût total et temps total
- Coût moyen par prise
- Respect de l'objectif hôpital (< 16h)

---

## 📝 Modifications possibles

Pour adapter l'algorithme :
- `src/analytics/plan_greedy.py` : modifier la fonction de difficulté
- `configs/costs.yaml` : ajuster les barèmes
- `src/analytics/work_organizer.py` : modifier la répartition des phases

---

**✅ Projet opérationnel !**
