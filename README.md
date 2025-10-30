# Planification-du-raccordement-lectrique-de-b-timents
Ce projet vise à répondre à la problématique suivante : Une petite ville a été touchée par des intempéries, entraînant la destruction de plusieurs infrastructures permettant le raccordement des maisons au réseau électrique. Vous avez été embauché par la mairie afin de proposer une planification pour les travaux à effectuer, dans le but de re-raccorder tous les citoyens au réseau électrique. L'objectif est de rétablir rapidement la connexion pour le plus grand nombre d'habitants avec le budget le plus faible possible

Il s'agit donc ici créer un plan de raccordement qui priorise les bâtiments les plus simples à raccorder (en minimisant les coûts) tout en maximisant le nombre de prises raccordées.

_____________________________________________________________________________________________________________

 2. Informations complémentaires à demander au client
A. Données manquantes ou contextuelles
1.Coordonnées géographiques précises des bâtiments (x, y ou shapefile complet).
2.Géométrie du réseau (tronçons : infrastructures.shp complet et à jour).
3.Typologie des bâtiments prioritaires : clarification sur la hiérarchie :
oNiveau 1 : hôpitaux, établissements de santé.
oNiveau 2 : écoles, bâtiments publics essentiels.
oNiveau 3 : résidentiel / commerce.	
4.Statut d’infrastructure — signification métier exacte de :
oinfra_intacte
oa_remplacer
5.Unités de mesure des longueurs (mètres, kilomètres ?).
6.Règles de mutualisation : une infrastructure partagée entre plusieurs bâtiments est-elle facturable une seule fois ou partiellement répartie ?
7.Calendrier de priorisation : contraintes temporelles (période d’intervention, fenêtres météo, contraintes logistiques).
8.Contexte géographique exact (système de projection CRS, zone, EPSG).
9.Indicateurs d’urgence ou d’importance socio-économique à intégrer.

 3. Stratégie de traitement des données (approche technique)
Phase	Description	Livrables techniques
1. Audit et normalisation	Vérification de la cohérence inter-fichiers (batiments, infra, reseau_en_arbre). Harmonisation des identifiants, suppression des doublons, validation des types et formats.	Rapport de cohérence et dictionnaire des champs.
2. Intégration et structuration	Fusion logique via les clés id_batiment ↔ infra_id. Création d’un modèle relationnel propre (tables Bâtiments, Infras, Réseau).	Base normalisée (.parquet ou .gpkg).
3. Enrichissement et typage	Attribution de métadonnées métier : catégories d’infra, typologie des bâtiments, criticité.	Table enrichie normalisée.
4. Construction du graphe réseau	Transformation du réseau linéaire (reseau_en_arbre) en graphe orienté (nodes = jonctions, edges = tronçons).	Graphe NetworkX validé.
5. Calculs d’indicateurs	Longueur cumulée, coût unitaire estimé, difficulté de raccordement, mutualisation, criticité.	Dataset d’indicateurs opérationnels.
6. Modélisation	Application de modèles de clustering non supervisé (K-Means, DBSCAN, HDBSCAN) ou de priorisation gloutonne.	Modèle priorisation/planification.
7. Restitution & QGIS	Export des résultats en couches SIG (GeoPackage/GeoJSON) pour intégration et visualisation.	Cartes thématiques et tableaux de bord.

 4. Hypothèses de travail
Domaine	Hypothèse technique	Risque associé
Topologie réseau	Le réseau est arborescent (pas de cycles, un seul chemin par bâtiment vers l’origine).	Si graphe cyclique → nécessité de traitement spécifique (pruning).
Unité de longueur	Toutes les longueurs sont exprimées en mètres.	Si incohérence d’unité → biais de coût.
Mutualisation	Une infrastructure partagée bénéficie d’un coût réparti proportionnellement au nombre de bâtiments.	Risque de double comptage si non confirmé.
Typologie d’infra	Les valeurs (aerien, fourreau, semi-aerien) sont exclusives et exhaustives.	Si valeurs hybrides → recalibrage nécessaire.
Priorisation métier	Les bâtiments prioritaires sont fournis exhaustivement (aucun manquant).	Risque de sous-évaluation des zones critiques.

 5. Contraintes identifiées
1.Données spatiales incomplètes : absence de coordonnées dans batiments.csv.
2.Présence de doublons dans le réseau logique (521 paires bâtiment–infra dupliquées).
3.Hétérogénéité de format (csv + xlsx + shapefile) → normalisation nécessaire.
4.Manque de typologie explicite des urgences (priorité à confirmer côté métier).
5.Manque de métadonnées (date de mise à jour, source, unité, version).

 6. Paramètres du modèle (placeholders)
Ces variables sont à calibrer selon le besoin métier et les retours client.
Paramètre	Type	Description
α_type_infra	Coefficient pondérateur	Pénalité selon type d’infrastructure (aérien < fourreau < semi-aérien).
β_criticity	Poids métier	Priorité attribuée selon type de bâtiment (hôpital, école, habitation).
γ_mutualisation	Ratio	Répartition du coût pour tronçons partagés.
θ_longueur	Fonction d’effort	Pondération basée sur la longueur totale du tronçon.
κ_repair_status	Binaire	0 = intact, 1 = à remplacer.
δ_budget_max	Seuil budgétaire	Limite du coût cumulé par période de planification.
λ_spatial_cluster	Paramètre de clustering	Rayon ou distance maximale pour regrouper les bâtiments à traiter ensemble.

 7. Qualité et validation des données (checklist)
Domaine	Contrôle	Méthode de vérification	Statut
Intégrité référentielle	id_batiment présents dans reseau_en_arbre	set(df_arbre.id_batiment) - set(df_bat.id_batiment)	
Typologie d’infrastructure	Valeurs dans liste contrôlée (aérien, fourreau, semi-aérien)	df_infra.type_infra.unique()	
Longueur non nulle	Pas de tronçons à longueur = 0	df_arbre[df_arbre['longueur']==0]	
Duplication réseau	Aucune paire (id_batiment, infra_id) dupliquée	df_arbre.duplicated(['id_batiment','infra_id'])	
Unité de longueur	Conversion explicite en mètre (float64)	Validation par échantillon	
Alignement inter-fichiers	Toutes les infra du réseau présentes dans infra.csv	✅ cohérent	
Données manquantes	Colonnes critiques non nulles	✅ complet	
Distribution des longueurs	Moyenne réaliste (≈30 m)	describe()	
Versioning / source	Date de mise à jour connue	—	

8. Stratégie de pilotage des prochaines étapes
1.Phase 1 — Validation métier :
Obtenir les précisions client sur les priorités, le statut des infras et les unités.
 Sortie : dictionnaire métier + jeu nettoyé.
2.Phase 2 — Intégration QGIS / SIG :
Créer des couches normalisées (Bâtiments, Infra, Réseau logique) et effectuer les jointures attributaires pour la visualisation.
3.Phase 3 — Modélisation et priorisation :
Implémentation du modèle glouton / clustering non supervisé (avec paramètres placeholders).
4.Phase 4 — Validation et ajustement :
Boucle de feedback client sur les zones prioritaires et les contraintes terrain.

Résumé exécutif
Jeu de données globalement cohérent (100% des clés croisées valides).
521 doublons à purger dans la table réseau.
Données spatialement incomplètes (pas de coordonnées des bâtiments).
Modèle prêt à être paramétré après validation métier.
Hypothèses structurantes à confirmer avant le passage à la modélisation.


Contributeurs : 

CHERIFI	Yacine
AKILAL	Adrien
SAICHI	Madjid
BOUNAB 	Abdenour
