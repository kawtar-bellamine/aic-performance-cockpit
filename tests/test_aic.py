"""Le classeur recalculé par LibreOffice et l'écran web donnent les mêmes chiffres que le calcul Python indépendant."""
import datetime as dt
from pathlib import Path

import openpyxl
import pytest

from aic.data import LINES, aic, enrich, gains, generate, kpis, maintenance, smed_day
from aic.recalc import recalculated
from aic.workbook import build

PLANT = generate()


@pytest.fixture(scope="module")
def xlsx(tmp_path_factory):
    return build(PLANT, tmp_path_factory.mktemp("x") / "aic.xlsx")


@pytest.fixture(scope="module")
def wb(xlsx):
    return recalculated(xlsx)


def test_no_formula_error(wb):
    bad = [(s.title, c.coordinate) for s in wb.worksheets for r in s.iter_rows() for c in r
           if isinstance(c.value, str) and (c.value.startswith("#") or "Err:" in c.value)]
    assert not bad


def test_dashboard_matches_python(wb):
    d = wb["Tableau de bord"]
    got = {d.cell(r, 2).value: d.cell(r, 6).value for r in range(10, 10 + len(kpis(PLANT)))}
    for lab, val in kpis(PLANT).items():
        assert got[lab] == pytest.approx(val, abs=1e-6), lab


@pytest.mark.parametrize("line", [c for c, *_ in LINES])
def test_aic_sheet_matches_python_for_each_line(xlsx, tmp_path, line):
    w = openpyxl.load_workbook(xlsx)
    w["AIC du jour"]["C5"] = line
    w.save(tmp_path / "l.xlsx")
    a = recalculated(tmp_path / "l.xlsx")["AIC du jour"]
    ref = aic(PLANT, line)
    assert a["B8"].value == pytest.approx(ref["trs"], abs=1e-9)
    assert (a["H8"].value, a["K8"].value, a["N8"].value, a["Q8"].value) == (
        ref["bonnes"], ref["objectif"], ref["arrets"], ref["rebuts"])
    assert (a["B11"].value, a["E11"].value, a["H11"].value) == (
        ref["jours_sans_accident"], ref["actions_ouvertes"], ref["actions_retard"])
    assert [a.cell(r, 12).value for r in (17, 18, 19)][:len(ref["top3"])] == [m for _, m in ref["top3"]]


def test_new_rows_are_counted(xlsx, tmp_path):
    """Une ligne saisie à la suite des données est prise en compte partout, formules calculées comprises."""
    w = openpyxl.load_workbook(xlsx)
    ws = w["Production"]
    k = 6 + len(PLANT.production)
    for col, v in zip(range(2, 8), [dt.date(2026, 11, 20), "Matin", "L1", 450, 800, 790]):
        ws.cell(k, col, v)
    w.save(tmp_path / "n.xlsx")
    r = recalculated(tmp_path / "n.xlsx")
    assert r["Tableau de bord"]["F14"].value == kpis(PLANT)["Pièces bonnes"] + 790
    assert r["Production"].cell(k, 15).value == pytest.approx(790 * 30 / 60 / 450)


def test_gains_sheet_matches_python(wb):
    g, ref = wb["Mesure des gains"], gains(PLANT, "L2", "Changement de série", smed_day())
    assert g["C14"].value == pytest.approx(ref["avant"]["trs"]) and g["E14"].value == pytest.approx(ref["apres"]["trs"])
    assert g["C15"].value == pytest.approx(ref["avant"]["min_par_equipe"])
    assert g["C20"].value == pytest.approx(ref["heures_an"]) and g["E20"].value == pytest.approx(ref["pieces_an"])
    assert ref["gain_trs_pts"] > 0                       # le SMED de démonstration améliore bien la ligne 2


def test_maintenance_matches_python(wb):
    d, ref = wb["Tableau de bord"], maintenance(PLANT)
    row = next(r for r in range(1, 80) if d.cell(r, 8).value == "Maintenance : pannes sur 12 semaines") + 2
    for i, (c, *_) in enumerate(LINES):
        assert d.cell(row + i, 9).value == ref[c]["pannes"]
        assert d.cell(row + i, 10).value == pytest.approx(ref[c]["mttr"])
        assert d.cell(row + i, 11).value == pytest.approx(ref[c]["mtbf"])


def test_trs_is_product_of_rates():
    e = enrich(PLANT)
    assert (e.disponibilite * e.performance * e.qualite - e.trs).abs().max() < 1e-12


def test_web_screen_matches_python(tmp_path):
    """L'écran web recalcule dans le navigateur : on compare ses chiffres à Python sur plusieurs jours et lignes."""
    sync = pytest.importorskip("playwright.sync_api")
    from aic.web import build as web
    page_file = web(tmp_path / "index.html")
    try:
        with sync.sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page()
            pg.goto(page_file.as_uri())
            for d in sorted(PLANT.production.date.unique())[-5:]:
                for line, *_ in LINES:
                    trs, good, stop = pg.evaluate(
                        f'() => {{ line="{line}"; day="{d.isoformat()}"; const a=agg(rows(x=>x===day)); return [a.trs,a.good,a.stop]; }}')
                    ref = aic(PLANT, line, d)
                    assert (trs, good, stop) == (pytest.approx(ref["trs"]), ref["bonnes"], ref["arrets"])
            b.close()
    except Exception as e:                                # navigateur absent sur la machine : test non applicable
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium non installé")
        raise
