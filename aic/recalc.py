"""Recalcule le classeur avec LibreOffice (sans Excel) et relit les valeurs : sert aux tests et au reporting."""
import shutil
import subprocess
import tempfile
from pathlib import Path

import openpyxl


def recalculated(xlsx: Path):
    d = Path(tempfile.mkdtemp())
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(d), str(xlsx)],
                   check=True, capture_output=True)
    wb = openpyxl.load_workbook(d / xlsx.name, data_only=True)
    shutil.rmtree(d)
    return wb
