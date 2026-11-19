"""Classeur Excel de pilotage de la performance et d'animation à intervalle court, sans macro.
Toute valeur calculée est une formule : on saisit la production, les arrêts, la sécurité et les actions, et l'AIC du
jour, le tableau de bord et la croix sécurité se mettent à jour."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.series import SeriesLabel
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

from .data import CAUSES, LINES, SHIFTS, SHIFTS_PER_YEAR, TODAY, WEEKS, Plant, smed_day, workdays

NAVY, STEEL, MIST, PAPER = "13233A", "5B6B7F", "E9EDF2", "F6F7F9"
GREEN, AMBER, RED, TEAL = "2E8B57", "D99A1E", "C0392B", "1F7A8C"
F = "Calibri"
thin = Side(style="thin", color="D5DBE3")
LINE_B = Border(bottom=thin)


def font(**k):
    return Font(name=F, **k)


def fill(c):
    return PatternFill("solid", fgColor=c)


def title(ws, text, sub):
    ws["B2"] = text
    ws["B2"].font = font(size=20, bold=True, color=NAVY)
    ws["B3"] = sub
    ws["B3"].font = font(size=10, italic=True, color=STEEL)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 2


def header(ws, row, col, labels, widths=None):
    for j, lab in enumerate(labels):
        c = ws.cell(row, col + j, lab)
        c.font = font(bold=True, color="FFFFFF", size=10)
        c.fill = fill(NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        if widths:
            ws.column_dimensions[L(col + j)].width = widths[j]
    ws.row_dimensions[row].height = 30


def table(ws, row, col, rows, fmts=None):
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            c = ws.cell(row + i, col + j, v)
            c.font = font(size=10)
            c.border = LINE_B
            if fmts and fmts[j]:
                c.number_format = fmts[j]


def tile(ws, r, c, label, formula, fmt, width=3):
    ws.merge_cells(start_row=r, start_column=c, end_row=r, end_column=c + width - 1)
    ws.merge_cells(start_row=r + 1, start_column=c, end_row=r + 1, end_column=c + width - 1)
    v = ws.cell(r, c, formula)
    v.font = font(size=24, bold=True, color=NAVY)
    v.number_format = fmt
    v.alignment = Alignment(horizontal="center", vertical="center")
    t = ws.cell(r + 1, c, label)
    t.font = font(size=9, color=STEEL)
    t.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
    for rr in (r, r + 1):
        for cc in range(c, c + width):
            ws.cell(rr, cc).fill = fill(PAPER)
    ws.row_dimensions[r].height = 38
    ws.row_dimensions[r + 1].height = 28
    return v


EXTRA_PROD, EXTRA_STOPS, EXTRA_SAFETY, EXTRA_ACTIONS = 600, 2500, 200, 200   # lignes prêtes à la saisie


def calc_headers(ws, row, cols):
    """En-têtes des colonnes calculées en gris acier : on ne les saisit pas."""
    for c in cols:
        ws.cell(row, c).fill = fill(STEEL)


def validate(ws, formula, ref):
    dv = DataValidation(type="list", formula1=formula, allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(ref)


def build(p: Plant, path: Path) -> Path:
    wb = Workbook()
    readme = wb.active
    readme.title = "Lisez-moi"
    par = wb.create_sheet("Paramètres")
    aicws = wb.create_sheet("AIC du jour")
    dash = wb.create_sheet("Tableau de bord")
    cross = wb.create_sheet("Croix sécurité")
    gws = wb.create_sheet("Mesure des gains")
    kdef = wb.create_sheet("Indicateurs")
    prod = wb.create_sheet("Production")
    stp = wb.create_sheet("Arrêts")
    saf = wb.create_sheet("Sécurité")
    act = wb.create_sheet("Actions")

    # ------------------------------------------------------------------ Paramètres
    title(par, "Paramètres", "Date du jour, lignes, cibles et causes d'arrêt. En usage réel : remplacer la date par =AUJOURDHUI().")
    par["B5"], par["C5"] = "Date du jour", TODAY
    par["B6"], par["C6"] = "Date de l'AIC (veille ouvrée)", "=WORKDAY(C5,-1)"
    par["B7"], par["C7"] = "Temps requis par équipe (min)", 450
    for r in (5, 6, 7):
        par.cell(r, 2).font = font(size=10, color=STEEL)
        par.cell(r, 3).font = font(size=11, bold=True, color=NAVY)
    par["C5"].number_format = par["C6"].number_format = "dd/mm/yyyy"
    header(par, 9, 2, ["Code", "Ligne", "Temps de cycle (s)", "TRS cible", "Objectif pièces bonnes / équipe"],
           [26, 30, 16, 12, 18])
    table(par, 10, 2, [list(x) for x in LINES], [None, None, "0", "0%", "#,##0"])
    header(par, 14, 2, ["Cause d'arrêt", "Famille"])
    table(par, 15, 2, [[c, f] for c, f, *_ in CAUSES])
    n_l, n_c = len(LINES), len(CAUSES)
    LCODE, LCYC, LTGT, LGOAL = (f"Paramètres!$B$10:$B${9 + n_l}", f"Paramètres!$D$10:$D${9 + n_l}",
                                f"Paramètres!$E$10:$E${9 + n_l}", f"Paramètres!$F$10:$F${9 + n_l}")
    TODAYC, AICD = "Paramètres!$C$5", "Paramètres!$C$6"

    # ------------------------------------------------------------------ données
    title(stp, "Arrêts", "Un arrêt par ligne : date, équipe, ligne, cause et durée en minutes.")
    header(stp, 5, 2, ["Date", "Équipe", "Ligne", "Cause", "Famille", "Durée (min)"], [12, 12, 8, 24, 14, 12])
    st_rows = list(p.stops.itertuples())
    srows = []
    for i in range(len(st_rows) + EXTRA_STOPS):
        k = 6 + i
        fam = f'=IF(E{k}="","",INDEX(Paramètres!$C$15:$C${14 + n_c},MATCH(E{k},Paramètres!$B$15:$B${14 + n_c},0)))'
        r = st_rows[i] if i < len(st_rows) else None
        srows.append([r.date, r.equipe, r.ligne, r.cause, fam, r.duree] if r else [None, None, None, None, fam, None])
    table(stp, 6, 2, srows, ["dd/mm/yyyy", None, None, None, None, "0"])
    s_end = 5 + len(srows)
    calc_headers(stp, 5, [6])
    validate(stp, '"' + ",".join(SHIFTS) + '"', f"C6:C{s_end}")
    validate(stp, '"' + ",".join(x[0] for x in LINES) + '"', f"D6:D{s_end}")
    validate(stp, f"=Paramètres!$B$15:$B${14 + n_c}", f"E6:E{s_end}")
    SD, SE, SL, SC, SM = (f"Arrêts!$B$6:$B${s_end}", f"Arrêts!$C$6:$C${s_end}", f"Arrêts!$D$6:$D${s_end}",
                          f"Arrêts!$E$6:$E${s_end}", f"Arrêts!$G$6:$G${s_end}")

    title(prod, "Production", "Une ligne par équipe et par ligne. Arrêts, temps utile et TRS sont calculés.")
    heads = ["Date", "Équipe", "Ligne", "Temps requis (min)", "Pièces produites", "Pièces bonnes", "Arrêts (min)",
             "Cycle (s)", "Fonctionnement (min)", "Temps utile (min)", "Disponibilité", "Performance", "Qualité",
             "TRS", "TRS cible", "Semaine (lundi)"]
    header(prod, 5, 2, heads, [12, 12, 8, 11, 11, 11, 10, 9, 13, 12, 12, 12, 10, 9, 9, 12])
    pr_rows = list(p.production.itertuples())
    prows = []
    for i in range(len(pr_rows) + EXTRA_PROD):
        k = 6 + i
        g = lambda f: f'=IF($B{k}="","",{f})'
        calc = [g(f"SUMIFS({SM},{SD},B{k},{SE},C{k},{SL},D{k})"), g(f"INDEX({LCYC},MATCH(D{k},{LCODE},0))"),
                g(f"E{k}-H{k}"), g(f"G{k}*I{k}/60"), g(f"J{k}/E{k}"), g(f"F{k}*I{k}/60/J{k}"), g(f"G{k}/F{k}"),
                g(f"K{k}/E{k}"), g(f"INDEX({LTGT},MATCH(D{k},{LCODE},0))"), g(f"B{k}-WEEKDAY(B{k},3)")]
        r = pr_rows[i] if i < len(pr_rows) else None
        prows.append(([r.date, r.equipe, r.ligne, r.temps_requis, r.pieces, r.bonnes] if r else [None] * 6) + calc)
    table(prod, 6, 2, prows, ["dd/mm/yyyy", None, None, "0", "#,##0", "#,##0", "0", "0", "0", "0.0", "0.0%", "0.0%",
                              "0.0%", "0.0%", "0%", "dd/mm/yyyy"])
    p_end = 5 + len(prows)
    calc_headers(prod, 5, range(8, 18))
    validate(prod, '"' + ",".join(SHIFTS) + '"', f"C6:C{p_end}")
    validate(prod, '"' + ",".join(x[0] for x in LINES) + '"', f"D6:D{p_end}")
    prod.conditional_formatting.add(f"O6:O{p_end}", FormulaRule(formula=["O6<P6-0.05"], font=Font(color=RED, bold=True)))
    prod.conditional_formatting.add(f"O6:O{p_end}", FormulaRule(formula=["O6<P6"], font=Font(color=AMBER, bold=True)))
    prod.conditional_formatting.add(f"O6:O{p_end}", FormulaRule(formula=["O6>=P6"], font=Font(color=GREEN, bold=True)))
    PD, PL, PREQ, PPC, PGOOD, PSTOP, PUT, PWK = (f"Production!$B$6:$B${p_end}", f"Production!$D$6:$D${p_end}",
                                                 f"Production!$E$6:$E${p_end}", f"Production!$F$6:$F${p_end}",
                                                 f"Production!$G$6:$G${p_end}", f"Production!$H$6:$H${p_end}",
                                                 f"Production!$K$6:$K${p_end}", f"Production!$Q$6:$Q${p_end}")
    PFON = f"Production!$J$6:$J${p_end}"

    title(saf, "Sécurité", "Événements sécurité : presque-accident, soin bénin, accident sans arrêt.")
    header(saf, 5, 2, ["Date", "Ligne", "Type"], [12, 8, 22])
    table(saf, 6, 2, [[r.date, r.ligne, r.type] for r in p.safety.itertuples()], ["dd/mm/yyyy", None, None])
    f_end = 5 + len(p.safety) + EXTRA_SAFETY
    validate(saf, '"' + ",".join(x[0] for x in LINES) + '"', f"C6:C{f_end}")
    FD, FL, FT = f"Sécurité!$B$6:$B${f_end}", f"Sécurité!$C$6:$C${f_end}", f"Sécurité!$D$6:$D${f_end}"
    dv = DataValidation(type="list", formula1='"Presque-accident,Soin bénin,Accident sans arrêt"')
    saf.add_data_validation(dv)
    dv.add(f"D6:D{f_end}")

    title(act, "Plan d'actions", "Actions décidées en AIC : pilote, échéance, statut. Retard et état sont calculés.")
    header(act, 5, 2, ["N°", "Création", "Ligne", "Problème", "Action", "Pilote", "Échéance", "Statut", "Retard (j)", "État"],
           [7, 11, 7, 34, 46, 12, 11, 11, 9, 14])
    ac_rows = list(p.actions.itertuples())
    arows = []
    for i in range(len(ac_rows) + EXTRA_ACTIONS):
        k = 6 + i
        calc = [f'=IF(I{k}="","",IF(AND(I{k}<>"Soldée",H{k}<{TODAYC}),{TODAYC}-H{k},0))',
                f'=IF(I{k}="","",IF(I{k}="Soldée","Soldée",IF(J{k}>0,"En retard","Dans les délais")))']
        r = ac_rows[i] if i < len(ac_rows) else None
        arows.append(([r.id, r.creation, r.ligne, r.probleme, r.action, r.pilote, r.echeance, r.statut] if r else [None] * 8) + calc)
    table(act, 6, 2, arows, [None, "dd/mm/yyyy", None, None, None, None, "dd/mm/yyyy", None, "0", None])
    a_end = 5 + len(arows)
    calc_headers(act, 5, [10, 11])
    validate(act, '"' + ",".join(x[0] for x in LINES) + '"', f"D6:D{a_end}")
    dv2 = DataValidation(type="list", formula1='"Ouverte,En cours,Soldée"')
    act.add_data_validation(dv2)
    dv2.add(f"I6:I{a_end}")
    act.conditional_formatting.add(f"K6:K{a_end}", CellIsRule(operator="equal", formula=['"En retard"'], fill=fill("F6D5D1"), font=Font(color=RED, bold=True)))
    act.conditional_formatting.add(f"K6:K{a_end}", CellIsRule(operator="equal", formula=['"Soldée"'], font=Font(color="9AA5B1")))
    AL, AS, AE, AK = (f"Actions!$D$6:$D${a_end}", f"Actions!$I$6:$I${a_end}", f"Actions!$H$6:$H${a_end}",
                      f"Actions!$K$6:$K${a_end}")
    for ws in (act,):
        for row in ws.iter_rows(min_row=6, max_row=a_end, min_col=5, max_col=6):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")

    # ------------------------------------------------------------------ AIC du jour
    title(aicws, "AIC du jour", "Animation à intervalle court de 5 minutes : sécurité, qualité, production, actions. "
                                "Choisir la ligne en C5.")
    aicws["B5"], aicws["C5"] = "Ligne", "L3"
    aicws["E5"], aicws["F5"] = "Veille analysée", f"={AICD}"
    aicws["F5"].number_format = "dd/mm/yyyy"
    aicws.merge_cells("F5:G5")
    for c in ("B5", "E5"):
        aicws[c].font = font(size=10, color=STEEL)
    aicws["C5"].font = font(size=14, bold=True, color="FFFFFF")
    aicws["C5"].fill = fill(TEAL)
    aicws["C5"].alignment = Alignment(horizontal="center")
    aicws["F5"].font = font(size=12, bold=True, color=NAVY)
    dv3 = DataValidation(type="list", formula1=f'"{",".join(x[0] for x in LINES)}"')
    aicws.add_data_validation(dv3)
    dv3.add("C5")
    aicws["H5"] = f"=INDEX(Paramètres!$C$10:$C${9 + n_l},MATCH($C$5,{LCODE},0))"
    aicws["H5"].font = font(size=12, bold=True, color=STEEL)
    for col in range(2, 20):
        aicws.column_dimensions[L(col)].width = 10.5
    sel = f"{PL},$C$5,{PD},$F$5"
    tile(aicws, 8, 2, "TRS de la veille", f"=IFERROR(SUMIFS({PUT},{sel})/SUMIFS({PREQ},{sel}),0)", "0.0%")
    tile(aicws, 8, 5, "TRS cible", f"=INDEX({LTGT},MATCH($C$5,{LCODE},0))", "0%")
    tile(aicws, 8, 8, "Pièces bonnes", f"=SUMIFS({PGOOD},{sel})", "#,##0")
    tile(aicws, 8, 11, "Objectif de pièces bonnes", f"=INDEX({LGOAL},MATCH($C$5,{LCODE},0))*{len(SHIFTS)}", "#,##0")
    tile(aicws, 8, 14, "Minutes d'arrêt", f"=SUMIFS({PSTOP},{sel})", "0")
    tile(aicws, 8, 17, "Pièces rebutées", f"=SUMIFS({PPC},{sel})-SUMIFS({PGOOD},{sel})", "0")
    tile(aicws, 11, 2, "Jours sans accident (ligne)",
         f'=IF(COUNTIFS({FL},$C$5,{FT},"<>Presque-accident",{FT},"<>")=0,{7 * WEEKS},{TODAYC}-_xlfn.MAXIFS({FD},{FL},$C$5,{FT},"<>Presque-accident",{FT},"<>"))', "0")
    tile(aicws, 11, 5, "Actions ouvertes", f'=COUNTIFS({AL},$C$5,{AS},"<>Soldée")', "0")
    tile(aicws, 11, 8, "Actions en retard", f'=COUNTIFS({AL},$C$5,{AK},"En retard")', "0")
    aicws.conditional_formatting.add("B8", FormulaRule(formula=["$B$8<$E$8-0.05"], font=Font(color=RED, bold=True, size=24, name=F)))
    aicws.conditional_formatting.add("B8", FormulaRule(formula=["$B$8<$E$8"], font=Font(color=AMBER, bold=True, size=24, name=F)))
    aicws.conditional_formatting.add("B8", FormulaRule(formula=["$B$8>=$E$8"], font=Font(color=GREEN, bold=True, size=24, name=F)))
    aicws.conditional_formatting.add("H11", CellIsRule(operator="greaterThan", formula=["0"], font=Font(color=RED, bold=True, size=24, name=F)))

    aicws["B15"] = "Arrêts de la veille par cause"
    aicws["B15"].font = font(size=12, bold=True, color=NAVY)
    header(aicws, 16, 2, ["Cause", "", "", "Minutes", ""])
    aicws.merge_cells("B16:D16")
    crow = []
    for i, (c, *_) in enumerate(CAUSES):
        k = 17 + i
        crow.append([c, None, None, f"=SUMIFS({SM},{SL},$C$5,{SD},$F$5,{SC},B{k})", f"=E{k}+{(n_c - i) / 1000}"])
    table(aicws, 17, 2, crow)
    for i in range(n_c):
        aicws.merge_cells(start_row=17 + i, start_column=2, end_row=17 + i, end_column=4)
        aicws.cell(17 + i, 6).font = font(size=8, color="FFFFFF")
    aicws["H15"] = "Top 3 des arrêts : à traiter en priorité"
    aicws["H15"].font = font(size=12, bold=True, color=NAVY)
    header(aicws, 16, 8, ["Rang", "Cause", "", "", "Minutes"])
    aicws.merge_cells("I16:K16")
    end = 16 + n_c
    for rnk in range(1, 4):
        k = 16 + rnk
        aicws.cell(k, 8, rnk).font = font(bold=True, color=TEAL, size=12)
        aicws.cell(k, 9, f"=IF(LARGE($F$17:$F${end},{rnk})<1,\"\",INDEX($B$17:$B${end},MATCH(LARGE($F$17:$F${end},{rnk}),$F$17:$F${end},0)))")
        aicws.merge_cells(start_row=k, start_column=9, end_row=k, end_column=11)
        aicws.cell(k, 12, f"=IF(I{k}=\"\",\"\",INDEX($E$17:$E${end},MATCH(LARGE($F$17:$F${end},{rnk}),$F$17:$F${end},0)))")
        for c in range(8, 13):
            aicws.cell(k, c).border = LINE_B
            aicws.cell(k, c).font = font(size=11, bold=c in (9, 12), color=NAVY if c != 8 else TEAL)
    aicws["H21"] = "Règle : un arrêt du top 3 sans action ouverte = une action décidée aujourd'hui (pilote, échéance)."
    aicws["H21"].font = font(size=9, italic=True, color=STEEL)

    # tendance 10 jours de la ligne choisie
    aicws["B27"] = "TRS des 10 derniers jours ouvrés"
    aicws["B27"].font = font(size=12, bold=True, color=NAVY)
    header(aicws, 28, 2, ["Jour", "TRS", "Cible"])
    for i in range(10):
        k = 29 + i
        aicws.cell(k, 2, f"=WORKDAY($F$5,{i - 9})").number_format = "dd/mm"
        aicws.cell(k, 3, f"=IFERROR(SUMIFS({PUT},{PL},$C$5,{PD},B{k})/SUMIFS({PREQ},{PL},$C$5,{PD},B{k}),NA())").number_format = "0.0%"
        aicws.cell(k, 4, "=$E$8").number_format = "0%"
        for c in (2, 3, 4):
            aicws.cell(k, c).font = font(size=10)
            aicws.cell(k, c).border = LINE_B
    ch = LineChart()
    ch.title, ch.height, ch.width = "TRS de la ligne et cible", 7.5, 16
    ch.add_data(Reference(aicws, min_col=3, min_row=28, max_row=38), titles_from_data=True)
    ch.add_data(Reference(aicws, min_col=4, min_row=28, max_row=38), titles_from_data=True)
    ch.set_categories(Reference(aicws, min_col=2, min_row=29, max_row=38))
    ch.series[0].graphicalProperties.line.solidFill = TEAL
    ch.series[0].graphicalProperties.line.width = 28000
    ch.series[1].graphicalProperties.line.solidFill = RED
    ch.series[1].graphicalProperties.line.dashStyle = "dash"
    ch.y_axis.number_format = "0%"
    ch.y_axis.majorGridlines = None
    aicws.add_chart(ch, "F27")

    # ------------------------------------------------------------------ Tableau de bord
    title(dash, "Tableau de bord", f"Performance du site sur {WEEKS} semaines. Données de démonstration, entièrement fictives.")
    for col in range(2, 22):
        dash.column_dimensions[L(col)].width = 10.5
    four = f"{PD},\">=\"&({TODAYC}-28)"
    tile(dash, 5, 2, "TRS site, 12 semaines", f"=SUM({PUT})/SUM({PREQ})", "0.0%")
    tile(dash, 5, 5, "TRS site, 4 dernières semaines", f"=SUMIFS({PUT},{four})/SUMIFS({PREQ},{four})", "0.0%")
    tile(dash, 5, 8, "Heures d'arrêt", f"=ROUND(SUM({PSTOP})/60,1)", "#,##0.0")
    tile(dash, 5, 11, "Actions en retard", f'=COUNTIF({AK},"En retard")', "0")
    tile(dash, 5, 14, "Jours sans accident (site)",
         f'=IF(COUNTIFS({FT},"<>Presque-accident",{FT},"<>")=0,{7 * WEEKS},{TODAYC}-_xlfn.MAXIFS({FD},{FT},"<>Presque-accident",{FT},"<>"))', "0")
    dash.conditional_formatting.add("K5", CellIsRule(operator="greaterThan", formula=["0"], font=Font(color=RED, bold=True, size=24, name=F)))

    dash["B9"] = "Indicateurs"
    dash["B9"].font = font(size=12, bold=True, color=NAVY)
    kp = [
        ("TRS site (12 semaines)", f"=SUM({PUT})/SUM({PREQ})", "0.0%"),
        ("TRS site (4 dernières semaines)", "=E5", "0.0%"),
        ("Disponibilité site", f"=(SUM({PREQ})-SUM({PSTOP}))/SUM({PREQ})", "0.0%"),
        ("Taux de qualité site", f"=SUM({PGOOD})/SUM({PPC})", "0.0%"),
        ("Pièces bonnes", f"=SUM({PGOOD})", "#,##0"),
        ("Heures d'arrêt", "=H5", "#,##0.0"),
        ("Actions ouvertes", f'=COUNTIFS({AS},"<>Soldée",{AS},"<>")', "0"),
        ("Actions en retard", "=K5", "0"),
        ("Taux de réalisation des actions", f'=COUNTIF({AS},"Soldée")/COUNTA({AS})', "0%"),
        ("Jours sans accident (site)", "=N5", "0"),
    ] + [(f"TRS {c} (12 semaines)", f"=SUMIFS({PUT},{PL},\"{c}\")/SUMIFS({PREQ},{PL},\"{c}\")", "0.0%") for c, *_ in LINES]
    for i, (lab, f_, fmt) in enumerate(kp):
        k = 10 + i
        dash.merge_cells(start_row=k, start_column=2, end_row=k, end_column=5)
        dash.cell(k, 2, lab).font = font(size=10)
        v = dash.cell(k, 6, f_)
        v.font = font(size=10, bold=True, color=NAVY)
        v.number_format = fmt
        v.alignment = Alignment(horizontal="right")
        for c in range(2, 7):
            dash.cell(k, c).border = LINE_B
    kp_end = 9 + len(kp)

    # TRS hebdomadaire par ligne
    days = workdays(TODAY, WEEKS)
    mondays = sorted({d - dt.timedelta(days=d.weekday()) for d in days})
    dash["H9"] = "TRS hebdomadaire par ligne"
    dash["H9"].font = font(size=12, bold=True, color=NAVY)
    header(dash, 10, 8, ["Semaine du"] + [c for c, *_ in LINES])
    for i, m in enumerate(mondays):
        k = 11 + i
        dash.cell(k, 8, m).number_format = "dd/mm"
        for j, (c, *_) in enumerate(LINES):
            dash.cell(k, 9 + j, f"=IFERROR(SUMIFS({PUT},{PL},\"{c}\",{PWK},$H{k})/SUMIFS({PREQ},{PL},\"{c}\",{PWK},$H{k}),NA())").number_format = "0.0%"
        for c in range(8, 12):
            dash.cell(k, c).font = font(size=10)
            dash.cell(k, c).border = LINE_B
    w_end = 10 + len(mondays)
    lc = LineChart()
    lc.title, lc.height, lc.width = "TRS hebdomadaire par ligne", 8, 17
    lc.add_data(Reference(dash, min_col=9, max_col=11, min_row=10, max_row=w_end), titles_from_data=True)
    lc.set_categories(Reference(dash, min_col=8, min_row=11, max_row=w_end))
    for s, col in zip(lc.series, (NAVY, TEAL, AMBER)):
        s.graphicalProperties.line.solidFill = col
        s.graphicalProperties.line.width = 26000
        s.smooth = False
    lc.y_axis.number_format = "0%"
    lc.y_axis.scaling.min = 0.5
    lc.y_axis.majorGridlines = None
    dash.add_chart(lc, "M9")

    # Pareto des arrêts sur la période
    pr0 = max(kp_end, w_end) + 3
    dash.cell(pr0, 2, "Pareto des arrêts sur 12 semaines").font = font(size=12, bold=True, color=NAVY)
    header(dash, pr0 + 1, 2, ["Cause", "", "", "Heures", "% cumulé"])
    dash.merge_cells(start_row=pr0 + 1, start_column=2, end_row=pr0 + 1, end_column=4)
    base = pr0 + 2
    hidden = pr0 + 2 + n_c + 2
    dash.cell(hidden - 1, 9, "")
    for i, (c, *_) in enumerate(CAUSES):
        k = hidden + i
        dash.cell(k, 9, c).font = font(size=8, color="FFFFFF")
        dash.cell(k, 10, f"=SUMIFS({SM},{SC},I{k})/60+{(n_c - i) / 100000}").font = font(size=8, color="FFFFFF")
    HK, HC = f"$J${hidden}:$J${hidden + n_c - 1}", f"$I${hidden}:$I${hidden + n_c - 1}"
    for r in range(n_c):
        k = base + r
        dash.cell(k, 2, f"=INDEX({HC},MATCH(LARGE({HK},{r + 1}),{HK},0))")
        dash.merge_cells(start_row=k, start_column=2, end_row=k, end_column=4)
        dash.cell(k, 5, f"=ROUND(LARGE({HK},{r + 1}),1)").number_format = "0.0"
        dash.cell(k, 6, f"=SUM($E${base}:E{k})/SUM($E${base}:$E${base + n_c - 1})").number_format = "0%"
        for c in range(2, 7):
            dash.cell(k, c).font = font(size=10)
            dash.cell(k, c).border = LINE_B
    bc = BarChart()
    bc.type, bc.title, bc.height, bc.width = "col", "Pareto des arrêts (heures)", 8, 17
    bc.add_data(Reference(dash, min_col=5, min_row=base - 1, max_row=base + n_c - 1), titles_from_data=True)
    bc.set_categories(Reference(dash, min_col=2, min_row=base, max_row=base + n_c - 1))
    bc.series[0].graphicalProperties.solidFill = NAVY
    bc.legend = None
    bc.y_axis.majorGridlines = None
    dash.add_chart(bc, f"M{pr0}")

    # maintenance : pannes, MTTR, MTBF par ligne
    SF = f"Arrêts!$F$6:$F${s_end}"
    dash.cell(pr0, 8, "Maintenance : pannes sur 12 semaines").font = font(size=12, bold=True, color=NAVY)
    header(dash, pr0 + 1, 8, ["Ligne", "Pannes", "MTTR (min)", "MTBF (h)"])
    for i, (c, *_) in enumerate(LINES):
        k = pr0 + 2 + i
        dash.cell(k, 8, c)
        dash.cell(k, 9, f'=COUNTIFS({SL},"{c}",{SF},"Panne")')
        dash.cell(k, 10, f'=IFERROR(AVERAGEIFS({SM},{SL},"{c}",{SF},"Panne"),0)').number_format = "0.0"
        dash.cell(k, 11, f'=IFERROR(SUMIFS({PFON},{PL},"{c}")/60/I{k},0)').number_format = "0.0"
        for cc in range(8, 12):
            dash.cell(k, cc).font = font(size=10)
            dash.cell(k, cc).border = LINE_B
    dash.cell(pr0 + 6, 8, "MTBF : heures de fonctionnement entre deux pannes. MTTR : durée moyenne d'une panne.").font = font(size=8.5, italic=True, color=STEEL)

    # ------------------------------------------------------------------ Mesure des gains
    title(gws, "Mesure des gains d'une action", "Comparer une ligne avant et après la mise en place d'une action, "
                                                 "sur des fenêtres de même durée. Saisir les 4 cellules en C.")
    for col, w in zip("BCDEFGHIJK", [30, 22, 4, 16, 16, 16, 4, 16, 16, 16]):
        gws.column_dimensions[col].width = w
    inputs = [("Ligne", "L2"), ("Cause d'arrêt suivie", "Changement de série"), ("Date de mise en place", smed_day()),
              ("Fenêtre (semaines)", 4)]
    for i, (lab, val) in enumerate(inputs):
        gws.cell(5 + i, 2, lab).font = font(size=10, color=STEEL)
        c = gws.cell(5 + i, 3, val)
        c.font = font(size=11, bold=True, color=NAVY)
        c.fill = fill("FFF6DD")
    gws["C7"].number_format = "dd/mm/yyyy"
    validate(gws, '"' + ",".join(x[0] for x in LINES) + '"', "C5")
    validate(gws, f"=Paramètres!$B$15:$B${14 + n_c}", "C6")
    gws["B10"], gws["C10"] = "Début de la fenêtre « avant »", "=C7-7*C8"
    gws["B11"], gws["C11"] = "Fin de la fenêtre « après »", f"=MIN(C7+7*C8,{TODAYC})"
    for r in (10, 11):
        gws.cell(r, 2).font = font(size=9, color=STEEL)
        gws.cell(r, 3).number_format = "dd/mm/yyyy"
        gws.cell(r, 3).font = font(size=10)
    bef = f'{PL},$C$5,{PD},">="&$C$10,{PD},"<"&$C$7'
    aft = f'{PL},$C$5,{PD},">="&$C$7,{PD},"<"&$C$11'
    sbef = f'{SL},$C$5,{SC},$C$6,{SD},">="&$C$10,{SD},"<"&$C$7'
    saft = f'{SL},$C$5,{SC},$C$6,{SD},">="&$C$7,{SD},"<"&$C$11'
    header(gws, 13, 2, ["Indicateur", "Avant", "", "Après", "Écart"])
    rows_g = [
        ("TRS de la ligne", f"=SUMIFS({PUT},{bef})/SUMIFS({PREQ},{bef})", f"=SUMIFS({PUT},{aft})/SUMIFS({PREQ},{aft})", "0.0%"),
        ("Minutes de la cause par équipe", f"=SUMIFS({SM},{sbef})/COUNTIFS({bef})", f"=SUMIFS({SM},{saft})/COUNTIFS({aft})", "0.0"),
        ("Durée moyenne d'un arrêt (min)", f"=IFERROR(AVERAGEIFS({SM},{sbef}),0)", f"=IFERROR(AVERAGEIFS({SM},{saft}),0)", "0.0"),
        ("Équipes observées", f"=COUNTIFS({bef})", f"=COUNTIFS({aft})", "0"),
    ]
    for i, (lab, fb, fa, fmt) in enumerate(rows_g):
        k = 14 + i
        gws.cell(k, 2, lab)
        gws.cell(k, 3, fb).number_format = fmt
        gws.cell(k, 5, fa).number_format = fmt
        if fmt == "0.0%":
            gws.cell(k, 6, f"=(E{k}-C{k})*100").number_format = '+0.0" pts";-0.0" pts"'
        else:
            gws.cell(k, 6, f"=E{k}-C{k}").number_format = "+0.0;-0.0;0"
        for c in (2, 3, 5, 6):
            gws.cell(k, c).font = font(size=10, bold=c == 6, color=NAVY)
            gws.cell(k, c).border = LINE_B
    cyc = f"INDEX({LCYC},MATCH($C$5,{LCODE},0))"
    tile(gws, 20, 2, "Gain de TRS (points)", "=(E14-C14)*100", "+0.0;-0.0", width=1)
    tile(gws, 20, 3, "Heures libérées par an", f"=(C15-E15)*{SHIFTS_PER_YEAR}/60", "#,##0", width=1)
    tile(gws, 20, 5, "Pièces bonnes en plus par an", f"=(C15-E15)*{SHIFTS_PER_YEAR}/60*3600/{cyc}", "#,##0", width=2)
    gws["B23"] = (f"Hypothèse annuelle : {SHIFTS_PER_YEAR} équipes par an ({len(SHIFTS)} équipes, 5 jours, 52 semaines). "
                  "Le gain est une estimation à confirmer dans la durée par le suivi du TRS.")
    gws["B23"].font = font(size=9, italic=True, color=STEEL)
    gc = BarChart()
    gc.type, gc.title, gc.height, gc.width = "col", "Minutes de la cause par équipe", 7, 12
    gws["H13"], gws["I13"], gws["H14"], gws["H15"] = "", "Minutes", "Avant", "Après"
    gws["I14"], gws["I15"] = "=C15", "=E15"
    for c in ("H13", "I13", "H14", "H15", "I14", "I15"):
        gws[c].font = font(size=8, color="FFFFFF")
    gc.add_data(Reference(gws, min_col=9, min_row=13, max_row=15), titles_from_data=True)
    gc.set_categories(Reference(gws, min_col=8, min_row=14, max_row=15))
    gc.series[0].graphicalProperties.solidFill = TEAL
    gc.legend = None
    gc.y_axis.majorGridlines = None
    gws.add_chart(gc, "H5")

    # ------------------------------------------------------------------ Dictionnaire des indicateurs
    title(kdef, "Dictionnaire des indicateurs", "Une définition unique par indicateur : la base d'un reporting "
                                               "fiable, sans doublon ni chiffre contesté.")
    heads = ["Indicateur", "Définition", "Calcul", "Unité", "Source", "Fréquence", "Responsable", "Cible", "Sens"]
    header(kdef, 5, 2, heads, [22, 40, 40, 8, 18, 12, 18, 12, 9])
    defs = [
        ("TRS", "Part du temps requis réellement transformée en pièces bonnes", "Temps utile ÷ temps requis ; temps utile = pièces bonnes × temps de cycle", "%", "Production, Arrêts", "Équipe", "Chef d'équipe", "Par ligne", "Hausse"),
        ("Disponibilité", "Part du temps requis sans arrêt", "(Temps requis − arrêts) ÷ temps requis", "%", "Arrêts", "Équipe", "Chef d'équipe", "", "Hausse"),
        ("Performance", "Vitesse réelle par rapport à la cadence nominale", "Pièces produites × temps de cycle ÷ temps de fonctionnement", "%", "Production", "Équipe", "Méthodes", "", "Hausse"),
        ("Qualité", "Part des pièces bonnes du premier coup", "Pièces bonnes ÷ pièces produites", "%", "Production", "Équipe", "Qualité", "≥ 98 %", "Hausse"),
        ("Pièces bonnes / objectif", "Production conforme rapportée à l'objectif de l'équipe", "Somme des pièces bonnes ÷ objectif × équipes", "%", "Production, Paramètres", "Équipe", "Chef d'équipe", "100 %", "Hausse"),
        ("Top 3 des arrêts", "Les trois causes qui ont coûté le plus de minutes la veille", "Somme des durées par cause, classement décroissant", "min", "Arrêts", "Jour", "Animateur AIC", "", "Baisse"),
        ("MTTR", "Durée moyenne d'une panne", "Somme des durées de panne ÷ nombre de pannes", "min", "Arrêts (famille Panne)", "Mois", "Maintenance", "", "Baisse"),
        ("MTBF", "Temps de fonctionnement moyen entre deux pannes", "Temps de fonctionnement ÷ nombre de pannes", "h", "Production, Arrêts", "Mois", "Maintenance", "", "Hausse"),
        ("Jours sans accident", "Jours écoulés depuis le dernier accident (hors presque-accident)", "Date du jour − date du dernier accident", "j", "Sécurité", "Jour", "Responsable HSE", "", "Hausse"),
        ("Actions en retard", "Actions non soldées dont l'échéance est dépassée", "Nombre d'actions avec statut ≠ Soldée et échéance < aujourd'hui", "nb", "Actions", "Jour", "Animateur AIC", "0", "Baisse"),
        ("Taux de réalisation", "Part des actions soldées", "Actions soldées ÷ actions décidées", "%", "Actions", "Semaine", "Responsable de production", "≥ 80 %", "Hausse"),
        ("Gain d'une action", "Effet mesuré d'une action sur la ligne", "Écart avant/après sur des fenêtres de même durée", "pts, h/an", "Production, Arrêts", "Après action", "Pilote de l'action", "", "Hausse"),
    ]
    table(kdef, 6, 2, [list(d) for d in defs])
    for row in kdef.iter_rows(min_row=6, max_row=5 + len(defs), min_col=2, max_col=10):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    for i in range(len(defs)):
        kdef.cell(6 + i, 2).font = font(size=10, bold=True, color=NAVY)

    # ------------------------------------------------------------------ Croix sécurité
    title(cross, "Croix sécurité", "Mois en cours, site : vert sans événement, orange presque-accident, rouge accident.")
    first = TODAY.replace(day=1)
    nxt = (first + dt.timedelta(days=32)).replace(day=1)
    ndays = (nxt - first).days
    cross["B5"] = first.strftime("%m/%Y")
    cross["B5"].font = font(size=14, bold=True, color=NAVY)
    # disposition en croix 7 x 7 : bras de 2 cases de large
    cells = [(r, c) for r in range(7) for c in range(7) if (2 <= c <= 4) or (2 <= r <= 4)]
    for c in range(2, 10):
        cross.column_dimensions[L(c)].width = 7
    for i in range(min(ndays, len(cells))):
        r, c = cells[i]
        rr, cc = 7 + r, 2 + c
        day = first + dt.timedelta(days=i)
        cross.row_dimensions[rr].height = 34
        cell = cross.cell(rr, cc, f'=IF(DATE({day.year},{day.month},{day.day})>={TODAYC},"{day.day}",'
                                  f'IF(COUNTIFS({FD},DATE({day.year},{day.month},{day.day}),{FT},"<>Presque-accident",{FT},"<>")>0,"{day.day} A",'
                                  f'IF(COUNTIFS({FD},DATE({day.year},{day.month},{day.day}))>0,"{day.day} P","{day.day}")))')
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.font = font(size=11, bold=True, color="FFFFFF")
        cell.border = Border(left=Side(style="thin", color="FFFFFF"), right=Side(style="thin", color="FFFFFF"),
                             top=Side(style="thin", color="FFFFFF"), bottom=Side(style="thin", color="FFFFFF"))
        future = day >= TODAY or day.weekday() >= 5
        cell.fill = fill("C9D1DB" if future else GREEN)
        if not future:
            ref = f"{L(cc)}{rr}"
            cross.conditional_formatting.add(ref, FormulaRule(formula=[f'RIGHT({ref},1)="A"'], fill=fill(RED)))
            cross.conditional_formatting.add(ref, FormulaRule(formula=[f'RIGHT({ref},1)="P"'], fill=fill(AMBER)))
    cross["K8"], cross["K9"], cross["K10"], cross["K11"] = ("Légende", "Vert : aucun événement",
                                                            "Orange (P) : presque-accident", "Rouge (A) : accident")
    cross["K12"] = "Gris : jour à venir ou non travaillé"
    for r in range(8, 13):
        cross.cell(r, 11).font = font(size=10, bold=r == 8, color=NAVY if r == 8 else STEEL)

    # ------------------------------------------------------------------ Lisez-moi
    title(readme, "Pilotage de la performance et AIC", "Classeur de démonstration, sans macro. Données entièrement fictives.")
    lines = [
        "Objectif : donner à chaque équipe une animation à intervalle court (AIC) de 5 minutes, fondée sur des chiffres fiables,",
        "et au management un tableau de bord de la performance (TRS, arrêts, sécurité, actions).",
        "",
        "Onglets",
        "AIC du jour : la veille de la ligne choisie, son top 3 des arrêts, la sécurité et les actions en retard.",
        "Tableau de bord : TRS du site et par ligne, tendance hebdomadaire, Pareto des arrêts.",
        "Croix sécurité : le mois en cours, jour par jour.",
        "Mesure des gains : l'effet d'une action, avant et après, en points de TRS, heures et pièces par an.",
        "Indicateurs : le dictionnaire des indicateurs (définition, calcul, source, fréquence, responsable).",
        "Production, Arrêts, Sécurité, Actions : les données saisies ; toutes les colonnes calculées sont des formules.",
        "Paramètres : date du jour, lignes, temps de cycle, cibles, causes d'arrêt.",
        "Saisie : ajouter les nouvelles lignes à la suite ; listes déroulantes pour l'équipe, la ligne, la cause et le statut.",
        "Les en-têtes bleu foncé sont à saisir, les en-têtes gris sont calculés : ne pas les modifier.",
        "",
        "Calculs",
        "TRS = temps utile / temps requis, avec temps utile = pièces bonnes x temps de cycle.",
        "TRS = disponibilité x performance x qualité. Les agrégats somment les temps (pas de moyenne de pourcentages).",
        "Un événement « presque-accident » ne remet pas à zéro le compteur de jours sans accident.",
    ]
    for i, t in enumerate(lines):
        c = readme.cell(5 + i, 2, t)
        c.font = font(size=11, bold=t in ("Onglets", "Calculs"), color=NAVY if t in ("Onglets", "Calculs") else "333B45")
    readme.column_dimensions["B"].width = 120

    for ws in wb.worksheets:
        ws.sheet_properties.tabColor = {"AIC du jour": TEAL, "Tableau de bord": NAVY, "Croix sécurité": GREEN, "Mesure des gains": AMBER, "Indicateurs": NAVY}.get(ws.title, "B0B8C2")
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToHeight = 0
    for ws in (prod, stp, saf, act):
        ws.freeze_panes = "B6"
        ws.auto_filter.ref = f"B5:{L(ws.max_column)}{ws.max_row}"
    wb.active = 2
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
