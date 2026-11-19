# Kit Power BI : pilotage de la performance et AIC

1. **Obtenir les données** > Texte/CSV : importer les 7 fichiers `dim_*.csv` et `fait_*.csv`.
2. **Relations** (vue Modèle), toutes en un-à-plusieurs, filtre unidirectionnel :
   - `dim_date[date]` vers `fait_production[date]`, `fait_arrets[date]`, `fait_securite[date]`
   - `dim_ligne[ligne]` vers `fait_production[ligne]`, `fait_arrets[ligne]`, `fait_securite[ligne]`, `fait_actions[ligne]`
   - `dim_cause[cause]` vers `fait_arrets[cause]`
3. **Mesures** : créer une table vide `_Mesures`, puis coller le contenu de `mesures.dax` (une mesure par bloc).
4. **Thème** : Affichage > Thèmes > Parcourir > `theme_aic.json`.
5. **Pages conseillées**
   - *AIC du jour* : segment Ligne et Date (veille), cartes TRS, TRS cible, Pièces bonnes, Arrêts, Jours sans accident,
     Actions en retard ; histogramme des arrêts par cause (Top N = 3) ; table des actions ouvertes.
   - *Tableau de bord* : courbe TRS par semaine et par ligne avec ligne de cible, Pareto (histogramme + % cumulé),
     cascade Temps requis > Arrêts > Ralentissements > Non-qualité > Temps utile.
   - *Maintenance et gains* : table Pannes, MTTR, MTBF par ligne ; cartes TRS avant, TRS après, Gain de TRS
     (filtrer sur la ligne L2 pour l'exemple du SMED).
6. **Couleur conditionnelle** : sur les cartes TRS, Mise en forme > Valeur > fx > Valeur du champ > `Couleur TRS`.

Le même modèle en étoile s'importe tel quel dans Qlik Sense ou tout autre outil de BI.

Les mêmes règles de calcul que le classeur Excel : le TRS est un rapport de temps (temps utile / temps requis),
jamais une moyenne de pourcentages.
