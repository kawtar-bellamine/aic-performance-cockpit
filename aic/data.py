"""Données de démonstration, entièrement fictives : une usine de 3 lignes, 2 équipes par jour, 12 semaines.
Production par équipe, arrêts détaillés par cause, événements sécurité et plan d'actions de l'animation à
intervalle court (AIC). Une graine fixe rend le jeu de données reproductible."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

TODAY = dt.date(2026, 11, 20)          # l'AIC du jour analyse la veille ouvrée
WEEKS = 12
SHIFTS = ["Matin", "Après-midi"]
REQUIRED_MIN = 450                     # 8 h d'ouverture moins 30 min de pauses

# code, nom, temps de cycle (s), TRS cible, objectif de pièces bonnes par équipe
LINES = [
    ("L1", "Ligne 1 · Assemblage", 30, 0.75, 680),
    ("L2", "Ligne 2 · Conditionnement", 20, 0.80, 1080),
    ("L3", "Ligne 3 · Usinage", 75, 0.65, 235),
]
# cause, famille, durée moyenne (min), fréquence moyenne par équipe pour L1, L2, L3
CAUSES = [
    ("Panne mécanique", "Panne", 28, (0.25, 0.15, 0.55)),
    ("Panne électrique", "Panne", 22, (0.12, 0.10, 0.18)),
    ("Changement de série", "Réglage", 35, (0.55, 0.70, 0.30)),
    ("Réglage qualité", "Réglage", 15, (0.30, 0.20, 0.35)),
    ("Manque matière", "Logistique", 18, (0.30, 0.25, 0.15)),
    ("Attente cariste", "Logistique", 9, (0.40, 0.30, 0.10)),
    ("Micro-arrêts", "Micro-arrêts", 4, (2.2, 3.5, 0.8)),
    ("Nettoyage non planifié", "Organisation", 12, (0.15, 0.25, 0.10)),
]
SAFETY_TYPES = ["Presque-accident", "Soin bénin", "Accident sans arrêt"]
PILOTS = ["M. Leroy", "S. Dubois", "N. Garcia", "C. Fontaine", "A. Mercier"]


@dataclass
class Plant:
    production: pd.DataFrame
    stops: pd.DataFrame
    safety: pd.DataFrame
    actions: pd.DataFrame


def workdays(end: dt.date, weeks: int) -> list[dt.date]:
    start = end - dt.timedelta(days=7 * weeks)
    days, d = [], start
    while d < end:
        if d.weekday() < 5:
            days.append(d)
        d += dt.timedelta(days=1)
    return days


def generate(seed: int = 11) -> Plant:
    rng = np.random.default_rng(seed)
    days = workdays(TODAY, WEEKS)
    smed_day = days[len(days) // 2]                          # SMED déployé sur L2 à mi-période
    prod, stops = [], []
    for d in days:
        for s in SHIFTS:
            for li, (code, _, cycle, _, _) in enumerate(LINES):
                total = 0
                for cause, fam, mean_d, freq in CAUSES:
                    f = freq[li] * 1.75
                    if code == "L3" and cause == "Panne mécanique" and d >= days[-15]:
                        f *= 2.2                             # dérive récente de la broche de L3
                    n = rng.poisson(f)
                    for _ in range(n):
                        dur = mean_d * rng.gamma(2.0, 0.5)
                        if code == "L2" and cause == "Changement de série" and d >= smed_day:
                            dur *= 0.5                        # effet du SMED
                        dur = int(max(1, round(dur)))
                        if total + dur > REQUIRED_MIN * 0.55:
                            continue
                        total += dur
                        stops.append((d, s, code, cause, fam, dur))
                run = REQUIRED_MIN - total
                perf = float(np.clip(rng.normal(0.89 if code != "L3" else 0.86, 0.035), 0.74, 0.98))
                pieces = int(run * 60 / cycle * perf)
                defect = float(np.clip(rng.normal(0.018 if code != "L3" else 0.032, 0.008), 0.0, 0.08))
                bad = int(round(pieces * defect))
                prod.append((d, s, code, REQUIRED_MIN, pieces, pieces - bad))
    production = pd.DataFrame(prod, columns=["date", "equipe", "ligne", "temps_requis", "pieces", "bonnes"])
    stops = pd.DataFrame(stops, columns=["date", "equipe", "ligne", "cause", "famille", "duree"])

    saf = []
    for d in days:
        for code, *_ in LINES:
            if rng.random() < 0.06:
                saf.append((d, code, SAFETY_TYPES[int(rng.choice(3, p=[0.7, 0.22, 0.08]))]))
    safety = pd.DataFrame(saf, columns=["date", "ligne", "type"])

    acts = []
    problems = [
        ("L1", "Changement de série long", "Préparer les outillages en temps masqué (SMED)"),
        ("L1", "Attentes cariste en fin de poste", "Tournée cariste cadencée toutes les 45 min"),
        ("L1", "Manque de composants au bord de ligne", "Kanban deux bacs sur les 12 références critiques"),
        ("L1", "Réglages répétés du poste de vissage", "Standard de réglage illustré au poste"),
        ("L2", "Changement de série long", "Atelier SMED : séparer opérations internes et externes"),
        ("L2", "Micro-arrêts de l'étiqueteuse", "Nettoyer et régler les capteurs de présence"),
        ("L2", "Bourrages sur le convoyeur d'entrée", "Remplacer les guides usés"),
        ("L2", "Nettoyages non planifiés", "Intégrer le nettoyage au standard de fin de poste (5S)"),
        ("L3", "Pannes mécaniques de la broche", "Analyse 8D et changement préventif des roulements"),
        ("L3", "Rebuts dimensionnels", "Carte de contrôle sur la cote critique"),
        ("L3", "Réglage qualité long au démarrage", "Fiche de premier article et réglage de référence"),
        ("L3", "Attente de la maintenance", "Liste des pièces de rechange critiques au magasin"),
        ("L1", "Presque-accident au chargement des bacs", "Abaisser la hauteur de chargement (ergonomie)"),
        ("L2", "Soin bénin à la coupe des films", "Cutter de sécurité et rappel du port des gants"),
        ("L3", "Copeaux au sol autour de la machine", "Bac de rétention et nettoyage 5S en fin de poste"),
    ]
    k = 1
    for rep in range(3):
        for code, pb, act in problems:
            created = days[int(rng.integers(0, len(days)))]
            if rep == 2 and rng.random() < 0.5:
                continue
            due = created + dt.timedelta(days=int(rng.integers(5, 25)))
            if due < TODAY - dt.timedelta(days=10):
                status = "Soldée" if rng.random() < 0.85 else "En cours"
            elif due < TODAY:
                status = rng.choice(["Soldée", "En cours", "Ouverte"], p=[0.55, 0.3, 0.15])
            else:
                status = rng.choice(["Ouverte", "En cours", "Soldée"], p=[0.45, 0.4, 0.15])
            acts.append((f"A{k:03d}", created, code, pb, act, PILOTS[int(rng.integers(0, len(PILOTS)))], due,
                         str(status)))
            k += 1
    actions = pd.DataFrame(acts, columns=["id", "creation", "ligne", "probleme", "action", "pilote", "echeance",
                                          "statut"]).sort_values("creation").reset_index(drop=True)
    actions["id"] = [f"A{i + 1:03d}" for i in range(len(actions))]
    return Plant(production, stops, safety, actions)


# ---------------------------------------------------------------- indicateurs (référence Python)
def cycle_of(code: str) -> int:
    return next(c for l, _, c, _, _ in LINES if l == code)


def enrich(p: Plant) -> pd.DataFrame:
    """Une ligne par équipe et par ligne : arrêts, temps de fonctionnement, temps utile, TRS et ses trois taux."""
    pr = p.production.copy()
    st = p.stops.groupby(["date", "equipe", "ligne"]).duree.sum()
    pr["arrets"] = [int(st.get((r.date, r.equipe, r.ligne), 0)) for r in pr.itertuples()]
    pr["cycle"] = pr.ligne.map(cycle_of)
    pr["fonctionnement"] = pr.temps_requis - pr.arrets
    pr["utile"] = pr.bonnes * pr.cycle / 60
    pr["disponibilite"] = pr.fonctionnement / pr.temps_requis
    pr["performance"] = pr.pieces * pr.cycle / 60 / pr.fonctionnement
    pr["qualite"] = pr.bonnes / pr.pieces
    pr["trs"] = pr.utile / pr.temps_requis
    return pr


def trs(df: pd.DataFrame) -> float:
    return float(df.utile.sum() / df.temps_requis.sum()) if len(df) else 0.0


def last_workday(today: dt.date = TODAY) -> dt.date:
    d = today - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def days_without_accident(safety: pd.DataFrame, line: str | None, today: dt.date = TODAY) -> int:
    s = safety[safety.type != "Presque-accident"]
    if line:
        s = s[s.ligne == line]
    if not len(s):
        return 7 * WEEKS                       # aucun accident sur la période suivie
    return (today - max(s.date)).days


def aic(p: Plant, line: str, day: dt.date | None = None) -> dict:
    """Ce que l'équipe regarde en 5 minutes : la veille de la ligne, ses 3 premiers arrêts, la sécurité et les actions."""
    day = day or last_workday()
    e = enrich(p)
    code, name, cycle, target, goal = next(x for x in LINES if x[0] == line)
    y = e[(e.ligne == line) & (e.date == day)]
    st = p.stops[(p.stops.ligne == line) & (p.stops.date == day)].groupby("cause").duree.sum().sort_values(
        ascending=False)
    act = p.actions[p.actions.ligne == line]
    open_ = act[act.statut != "Soldée"]
    return {
        "trs": trs(y), "cible": target, "bonnes": int(y.bonnes.sum()), "objectif": goal * len(SHIFTS),
        "arrets": int(y.arrets.sum()), "rebuts": int((y.pieces - y.bonnes).sum()),
        "top3": [(c, int(v)) for c, v in st.head(3).items()],
        "actions_ouvertes": int(len(open_)), "actions_retard": int((open_.echeance < TODAY).sum()),
        "jours_sans_accident": days_without_accident(p.safety, line),
    }


def kpis(p: Plant) -> dict:
    """Indicateurs du tableau de bord sur les 12 semaines, tels qu'affichés dans le classeur."""
    e = enrich(p)
    four = e[e.date >= TODAY - dt.timedelta(days=28)]
    open_ = p.actions[p.actions.statut != "Soldée"]
    out = {
        "TRS site (12 semaines)": trs(e),
        "TRS site (4 dernières semaines)": trs(four),
        "Disponibilité site": float(e.fonctionnement.sum() / e.temps_requis.sum()),
        "Taux de qualité site": float(e.bonnes.sum() / e.pieces.sum()),
        "Pièces bonnes": int(e.bonnes.sum()),
        "Heures d'arrêt": round(float(e.arrets.sum() / 60), 1),
        "Actions ouvertes": int(len(open_)),
        "Actions en retard": int((open_.echeance < TODAY).sum()),
        "Taux de réalisation des actions": float((p.actions.statut == "Soldée").mean()),
        "Jours sans accident (site)": days_without_accident(p.safety, None),
    }
    for code, *_ in LINES:
        out[f"TRS {code} (12 semaines)"] = trs(e[e.ligne == code])
    return out


# ---------------------------------------------------------------- mesure des gains et maintenance
SHIFTS_PER_YEAR = len(SHIFTS) * 5 * 52


def smed_day() -> dt.date:
    """Date de mise en place du SMED sur la ligne 2 (milieu de la période de démonstration)."""
    days = workdays(TODAY, WEEKS)
    return days[len(days) // 2]


def gains(p: Plant, line: str, cause: str, start: dt.date, weeks: int = 4) -> dict:
    """Avant/après d'une action : fenêtres de `weeks` semaines de part et d'autre de la date de mise en place."""
    e = enrich(p)
    b0, a1 = start - dt.timedelta(days=7 * weeks), min(start + dt.timedelta(days=7 * weeks), TODAY)
    def win(lo, hi):
        pr = e[(e.ligne == line) & (e.date >= lo) & (e.date < hi)]
        st = p.stops[(p.stops.ligne == line) & (p.stops.cause == cause) & (p.stops.date >= lo) & (p.stops.date < hi)]
        n = len(pr)
        return {"trs": trs(pr), "min_par_equipe": float(st.duree.sum() / n) if n else 0.0,
                "duree_moyenne": float(st.duree.mean()) if len(st) else 0.0, "equipes": n}
    before, after = win(b0, start), win(start, a1)
    cycle = cycle_of(line)
    saved_h = (before["min_par_equipe"] - after["min_par_equipe"]) * SHIFTS_PER_YEAR / 60
    return {"avant": before, "apres": after, "gain_trs_pts": 100 * (after["trs"] - before["trs"]),
            "heures_an": saved_h, "pieces_an": saved_h * 3600 / cycle}


def maintenance(p: Plant) -> dict:
    """Pannes par ligne sur la période : nombre, MTTR (min) et MTBF (h de fonctionnement entre deux pannes)."""
    e = enrich(p)
    out = {}
    for code, *_ in LINES:
        pn = p.stops[(p.stops.ligne == code) & (p.stops.famille == "Panne")]
        run_h = float(e[e.ligne == code].fonctionnement.sum() / 60)
        n = len(pn)
        out[code] = {"pannes": n, "mttr": float(pn.duree.mean()) if n else 0.0, "mtbf": run_h / n if n else run_h}
    return out
