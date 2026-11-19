"""Écran d'animation AIC en page web autonome (python -m aic.web) : docs/index.html, publiable sur GitHub Pages.
Les données brutes sont embarquées et les indicateurs sont recalculés dans la page avec les mêmes règles qu'Excel."""
import json
import shutil
from pathlib import Path

from .data import CAUSES, LINES, SHIFTS, TODAY, WEEKS, enrich, gains, generate, kpis, last_workday, maintenance, smed_day

ROOT = Path(__file__).resolve().parents[1]


def payload() -> dict:
    p = generate()
    e = enrich(p)
    return dict(
        today=TODAY.isoformat(), aic_day=last_workday().isoformat(), weeks=WEEKS, shifts=SHIFTS,
        lines=[dict(code=c, name=n, cycle=cy, target=t, goal=g) for c, n, cy, t, g in LINES],
        causes=[dict(cause=c, family=f) for c, f, *_ in CAUSES],
        prod=[[r.date.isoformat(), r.equipe, r.ligne, int(r.temps_requis), int(r.pieces), int(r.bonnes), int(r.arrets)]
              for r in e.itertuples()],
        stops=[[r.date.isoformat(), r.ligne, r.cause, int(r.duree)] for r in p.stops.itertuples()],
        safety=[[r.date.isoformat(), r.ligne, r.type] for r in p.safety.itertuples()],
        actions=[dict(id=r.id, creation=r.creation.isoformat(), ligne=r.ligne, probleme=r.probleme, action=r.action,
                      pilote=r.pilote, echeance=r.echeance.isoformat(), statut=r.statut) for r in p.actions.itertuples()],
        kpis=kpis(p), maintenance=maintenance(p),
        gain=dict(line="L2", cause="Changement de série", start=smed_day().isoformat(), weeks=4,
                  action="SMED : outillages préparés en temps masqué", **gains(p, "L2", "Changement de série", smed_day())),
    )


def build(out: Path = ROOT / "docs/index.html") -> Path:
    html = (Path(__file__).parent / "templates/aic.html").read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(payload(), ensure_ascii=False))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    fonts = out.parent / "fonts"
    fonts.mkdir(exist_ok=True)
    for f in ("Inter-Regular.otf", "Inter-Medium.otf", "Inter-SemiBold.otf", "Inter-Bold.otf"):
        shutil.copy(ROOT / "assets/fonts" / f, fonts / f)
    return out


if __name__ == "__main__":
    print(build())
