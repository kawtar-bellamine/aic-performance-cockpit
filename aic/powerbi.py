"""Kit Power BI (python -m aic.powerbi) : modèle en étoile en CSV, mesures DAX et thème aux couleurs du projet.
Il suffit d'importer les CSV dans Power BI Desktop, de créer les relations indiquées et de coller les mesures."""
import datetime as dt
import json
from pathlib import Path

import pandas as pd

from .data import CAUSES, LINES, TODAY, enrich, generate, smed_day, workdays, WEEKS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "powerbi"

MEASURES = """// Mesures DAX : coller dans une table de mesures « _Mesures »
Temps requis (min) = SUM ( fait_production[temps_requis] )
Arrêts (min) = SUM ( fait_production[arrets] )
Temps utile (min) = SUM ( fait_production[temps_utile] )
Pièces produites = SUM ( fait_production[pieces] )
Pièces bonnes = SUM ( fait_production[bonnes] )

TRS = DIVIDE ( [Temps utile (min)], [Temps requis (min)] )
Disponibilité = DIVIDE ( [Temps requis (min)] - [Arrêts (min)], [Temps requis (min)] )
Qualité = DIVIDE ( [Pièces bonnes], [Pièces produites] )
Performance = DIVIDE ( [TRS], [Disponibilité] * [Qualité] )

TRS cible =
    DIVIDE (
        SUMX ( fait_production, fait_production[temps_requis] * RELATED ( dim_ligne[trs_cible] ) ),
        [Temps requis (min)]
    )
Écart à la cible (pts) = ( [TRS] - [TRS cible] ) * 100
Couleur TRS =
    SWITCH ( TRUE (),
        [TRS] >= [TRS cible], "#2E8B57",
        [TRS] >= [TRS cible] - 0.05, "#D99A1E",
        "#C0392B" )

Heures d'arrêt (cause) = DIVIDE ( SUM ( fait_arrets[duree] ), 60 )
% cumulé Pareto =
    VAR h = [Heures d'arrêt (cause)]
    VAR tot = CALCULATE ( [Heures d'arrêt (cause)], ALL ( dim_cause ) )
    VAR cum = SUMX ( FILTER ( ALL ( dim_cause ), [Heures d'arrêt (cause)] >= h ), [Heures d'arrêt (cause)] )
    RETURN DIVIDE ( cum, tot )

Pannes = CALCULATE ( COUNTROWS ( fait_arrets ), dim_cause[famille] = "Panne" )
MTTR (min) = DIVIDE ( CALCULATE ( SUM ( fait_arrets[duree] ), dim_cause[famille] = "Panne" ), [Pannes] )
MTBF (h) = DIVIDE ( ( [Temps requis (min)] - [Arrêts (min)] ) / 60, [Pannes] )

// Mesure des gains : comparer deux périodes de même durée autour de la date de mise en place d'une action
Date de mise en place = DATE ( __SY__, __SM__, __SD__ )
TRS avant = CALCULATE ( [TRS], DATESINPERIOD ( dim_date[date], [Date de mise en place] - 1, -28, DAY ) )
TRS après = CALCULATE ( [TRS], DATESINPERIOD ( dim_date[date], [Date de mise en place] + 27, -28, DAY ) )
Gain de TRS (pts) = ( [TRS après] - [TRS avant] ) * 100

Actions ouvertes = CALCULATE ( COUNTROWS ( fait_actions ), fait_actions[statut] <> "Soldée" )
Actions en retard =
    CALCULATE ( COUNTROWS ( fait_actions ), fait_actions[statut] <> "Soldée", fait_actions[echeance] < DATE ( __Y__, __M__, __D__ ) )
Taux de réalisation des actions = DIVIDE ( CALCULATE ( COUNTROWS ( fait_actions ), fait_actions[statut] = "Soldée" ), COUNTROWS ( fait_actions ) )

Jours sans accident =
    VAR last = CALCULATE ( MAX ( fait_securite[date] ), fait_securite[type] <> "Presque-accident" )
    RETURN IF ( ISBLANK ( last ), __N__, DATE ( __Y__, __M__, __D__ ) - last )
"""

THEME = {
    "name": "AIC performance",
    "dataColors": ["#13233A", "#1F7A8C", "#D99A1E", "#2E8B57", "#C0392B", "#6F8DB5", "#9AA5B1", "#5B6B7F"],
    "background": "#FFFFFF", "foreground": "#13233A", "tableAccent": "#1F7A8C",
    "good": "#2E8B57", "neutral": "#D99A1E", "bad": "#C0392B",
    "textClasses": {"title": {"fontFace": "Segoe UI Semibold", "color": "#13233A", "fontSize": 13},
                    "label": {"fontFace": "Segoe UI", "color": "#66768A", "fontSize": 10},
                    "callout": {"fontFace": "Segoe UI Semibold", "color": "#13233A", "fontSize": 28}},
    "visualStyles": {"*": {"*": {"background": [{"color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
                                 "border": [{"show": True, "color": {"solid": {"color": "#E3E8EE"}}, "radius": 12}]}}},
}


def build() -> Path:
    p = generate()
    e = enrich(p)
    OUT.mkdir(exist_ok=True)
    days = workdays(TODAY, WEEKS)
    pd.DataFrame({"date": [days[0] + dt.timedelta(days=i) for i in range((TODAY - days[0]).days)]}).assign(
        semaine=lambda d: d.date.map(lambda x: x - dt.timedelta(days=x.weekday())),
        mois=lambda d: d.date.map(lambda x: x.strftime("%Y-%m")),
        jour=lambda d: d.date.map(lambda x: ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"][x.weekday()]),
        jour_ouvre=lambda d: d.date.map(lambda x: x.weekday() < 5),
    ).to_csv(OUT / "dim_date.csv", index=False)
    pd.DataFrame(LINES, columns=["ligne", "nom", "temps_cycle_s", "trs_cible", "objectif_equipe"]).to_csv(
        OUT / "dim_ligne.csv", index=False)
    pd.DataFrame([(c, f) for c, f, *_ in CAUSES], columns=["cause", "famille"]).to_csv(OUT / "dim_cause.csv", index=False)
    e.rename(columns={"utile": "temps_utile"})[
        ["date", "equipe", "ligne", "temps_requis", "pieces", "bonnes", "arrets", "temps_utile"]].to_csv(
        OUT / "fait_production.csv", index=False)
    p.stops[["date", "equipe", "ligne", "cause", "duree"]].to_csv(OUT / "fait_arrets.csv", index=False)
    p.safety.to_csv(OUT / "fait_securite.csv", index=False)
    p.actions.to_csv(OUT / "fait_actions.csv", index=False)
    (OUT / "mesures.dax").write_text(
        MEASURES.replace("__Y__", str(TODAY.year)).replace("__M__", str(TODAY.month)).replace("__D__", str(TODAY.day))
        .replace("__N__", str(7 * WEEKS)).replace("__SY__", str(smed_day().year)).replace("__SM__", str(smed_day().month))
        .replace("__SD__", str(smed_day().day)), encoding="utf-8")
    (OUT / "theme_aic.json").write_text(json.dumps(THEME, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "LISEZMOI.md").write_text(GUIDE, encoding="utf-8")
    return OUT


GUIDE = """# Kit Power BI : pilotage de la performance et AIC

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
"""

if __name__ == "__main__":
    print(build())
