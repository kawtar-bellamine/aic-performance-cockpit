"""Génère les données de démonstration, le classeur Excel et le kit Power BI (python -m aic.build)."""
from pathlib import Path

from .data import generate
from .workbook import build

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "outputs/pilotage_performance_aic.xlsx"

if __name__ == "__main__":
    p = generate()
    print(build(p, XLSX))
