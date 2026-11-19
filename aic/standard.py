"""Standard d'animation AIC en une page A4 (python -m aic.standard) : déroulé de 5 minutes, rôles, règles, escalade.
À afficher sur le tableau d'animation de chaque ligne. Mise en page HTML imprimée par Chromium."""
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HTML = """<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>
@font-face { font-family: I; src: url("__F__/Inter-Regular.otf"); font-weight: 400; }
@font-face { font-family: I; src: url("__F__/Inter-SemiBold.otf"); font-weight: 600; }
@font-face { font-family: I; src: url("__F__/Inter-Bold.otf"); font-weight: 700; }
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font: 11px/1.5 I, sans-serif; color: #13233A; }
.page { width: 210mm; height: 297mm; padding: 14mm 15mm; position: relative; }
.top { background: #13233A; color: #fff; margin: -14mm -15mm 8mm; padding: 11mm 15mm 8mm; }
.eb { font-size: 8.5px; letter-spacing: .25em; text-transform: uppercase; color: #8FB3C2; }
h1 { font-size: 25px; margin: 4px 0 2px; font-weight: 700; } .sub { color: #B9C7D8; font-size: 11px; }
h2 { font-size: 11px; text-transform: uppercase; letter-spacing: .12em; color: #66768A; margin: 18px 0 8px; }
.time { display: grid; grid-template-columns: 1fr 1fr 2fr 1fr; gap: 6px; }
.s { border-radius: 10px; padding: 10px 11px; color: #fff; min-height: 104px; }
.s b { font-size: 26px; display: block; line-height: 1.1; margin-top: 4px; } .s .w { font-size: 13px; font-weight: 600; display: block; } .s .t { font-size: 9px; opacity: .85; letter-spacing: .1em; text-transform: uppercase; }
.s ul { margin: 6px 0 0; padding-left: 14px; font-size: 9.6px; } .s li { margin: 2px 0; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.box { border: 1px solid #E3E8EE; border-radius: 10px; padding: 10px 12px; }
.box h3 { margin: 0 0 6px; font-size: 11.5px; }
.box ul { margin: 0; padding-left: 15px; } .box li { margin: 3px 0; }
.esc { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; align-items: stretch; }
.lv { border-radius: 10px; padding: 10px 12px; background: #F3F5F8; border-top: 4px solid #1F7A8C; }
.lv b { font-size: 13px; } .lv .h { color: #66768A; font-size: 9.5px; margin: 2px 0 6px; }
.arrow { text-align: center; color: #66768A; font-size: 9px; margin-top: 4px; }
.foot { position: absolute; left: 15mm; right: 15mm; bottom: 9mm; display: flex; justify-content: space-between; font-size: 8px;
        color: #8A97A8; border-top: 1px solid #E3E8EE; padding-top: 5px; letter-spacing: .06em; text-transform: uppercase; }
.chk { display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px 14px; }
.chk div::before { content: ""; display: inline-block; width: 9px; height: 9px; border: 1.5px solid #1F7A8C; border-radius: 2px; margin-right: 7px; vertical-align: -1px; }
</style></head><body><div class="page">
<div class="top"><div class="eb">Standard d'animation · niveau 1 · ligne de production</div>
<h1>AIC de 5 minutes, debout, au tableau de la ligne</h1>
<div class="sub">Chaque jour à 8 h 40, en début de poste du matin. Les chiffres sont ceux de la veille, lus sur l'écran ou le classeur AIC.</div></div>

<h2>Déroulé minute par minute</h2>
<div class="time">
 <div class="s" style="background:#2E8B57"><span class="t">0 à 1 min</span><b>S</b><span class="w">Sécurité</span><ul><li>Jours sans accident</li><li>Croix sécurité de la veille</li><li>Presque-accidents : cause en une phrase</li></ul></div>
 <div class="s" style="background:#D99A1E"><span class="t">1 à 2 min</span><b>Q</b><span class="w">Qualité</span><ul><li>Taux de qualité, pièces rebutées</li><li>Réclamation ou alerte en cours</li></ul></div>
 <div class="s" style="background:#1F7A8C"><span class="t">2 à 4 min</span><b>P</b><span class="w">Production et TRS</span><ul><li>TRS de la veille contre la cible</li><li>Pièces bonnes contre l'objectif</li><li>Top 3 des arrêts : une action par arrêt sans action ouverte</li></ul></div>
 <div class="s" style="background:#13233A"><span class="t">4 à 5 min</span><b>A</b><span class="w">Actions</span><ul><li>Actions arrivées à échéance</li><li>Retards : nouvelle date ou escalade</li></ul></div>
</div>

<div class="grid2" style="margin-top:14px">
 <div class="box"><h3>Rôles</h3><ul>
  <li><b>Animateur</b> (chef d'équipe) : tient le temps, lit les chiffres, fait décider.</li>
  <li><b>Opérateurs de la ligne</b> : décrivent les arrêts vécus et proposent des solutions.</li>
  <li><b>Maintenance et qualité</b> : présents si un arrêt ou un défaut les concerne.</li>
  <li><b>Pilote d'action</b> : un nom, une échéance, jamais « l'équipe ».</li></ul></div>
 <div class="box"><h3>Règles</h3><ul>
  <li>5 minutes, à heure fixe, debout, même quand tout va bien.</li>
  <li>On constate et on décide ; on ne résout pas en séance. Au-delà d'une minute, le sujet sort de l'AIC.</li>
  <li>Une action = un problème, une action, un pilote, une échéance.</li>
  <li>Les chiffres sont mis à jour avant l'animation, pas pendant.</li></ul></div>
</div>

<h2>Escalade : un problème non résolu monte d'un niveau</h2>
<div class="esc">
 <div class="lv"><b>N1 · Ligne</b><div class="h">8 h 40 · 5 min · chef d'équipe</div>Arrêts, qualité, sécurité de la ligne. Escalade si une ressource ou une décision dépasse l'équipe.</div>
 <div class="lv" style="border-color:#D99A1E"><b>N2 · Atelier</b><div class="h">9 h 15 · 10 min · responsable de production</div>Synthèse des lignes, arbitrage maintenance et méthodes, actions en retard de plus de 5 jours.</div>
 <div class="lv" style="border-color:#C0392B"><b>N3 · Site</b><div class="h">10 h 00 · 15 min · direction</div>Investissements, sujets transverses, tendances du TRS du site sur 4 semaines.</div>
</div>
<div class="arrow">Le sujet descend avec une réponse et une date le jour même.</div>

<h2>Auto-évaluation de l'animation (chaque vendredi)</h2>
<div class="chk"><div>Démarrée à l'heure, durée tenue</div><div>Chiffres de la veille affichés et exacts</div>
<div>Sécurité traitée en premier</div><div>Top 3 des arrêts relié à des actions</div>
<div>Chaque action a un pilote et une échéance</div><div>Moins de 10 % d'actions en retard</div>
<div>Les opérateurs ont pris la parole</div><div>Les sujets longs sont sortis de l'AIC</div></div>


<h2>Lire le TRS en 30 secondes</h2>
<div class="grid2">
 <div class="box"><h3>TRS = disponibilité × performance × qualité</h3>
  <div>Autrement dit : temps utile ÷ temps requis, avec temps utile = pièces bonnes × temps de cycle.</div>
  <div style="margin-top:6px;color:#66768A">On additionne les temps avant de diviser : jamais de moyenne de pourcentages entre équipes ou lignes.</div></div>
 <div class="box"><h3>Où part le temps</h3>
  <div style="display:flex;gap:6px;align-items:flex-end;height:58px;margin-top:4px">
   <div style="width:20%;height:100%;background:#13233A;border-radius:4px"></div>
   <div style="width:20%;height:22%;background:#C0392B;border-radius:4px"></div>
   <div style="width:20%;height:12%;background:#D99A1E;border-radius:4px"></div>
   <div style="width:20%;height:5%;background:#C9D1DB;border-radius:4px"></div>
   <div style="width:20%;height:61%;background:#1F7A8C;border-radius:4px"></div></div>
  <div style="display:flex;gap:6px;font-size:8.5px;color:#66768A;margin-top:3px"><span style="width:20%">Requis</span><span style="width:20%">Arrêts</span><span style="width:20%">Ralentis.</span><span style="width:20%">Non-qualité</span><span style="width:20%">Utile</span></div></div>
</div>
<div class="foot"><span>Standard de démonstration · à adapter à chaque site</span><span>Pilotage de la performance · AIC</span></div>
</div></body></html>"""


def build(out: Path = ROOT / "outputs/standard_animation_AIC.pdf") -> Path:
    from playwright.sync_api import sync_playwright
    html = HTML.replace("__F__", (ROOT / "assets/fonts").as_uri())
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "s.html"
        f.write_text(html, encoding="utf-8")
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page()
            pg.goto(f.as_uri()); pg.wait_for_timeout(400)
            out.parent.mkdir(parents=True, exist_ok=True)
            pg.pdf(path=str(out), format="A4", print_background=True, prefer_css_page_size=True)
            b.close()
    return out


if __name__ == "__main__":
    print(build())
