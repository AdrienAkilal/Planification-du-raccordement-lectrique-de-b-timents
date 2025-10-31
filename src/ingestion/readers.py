# src/ingestion/readers.py
from pathlib import Path
import pandas as pd
import csv

EXCEL_SUFFIXES = {".xlsx", ".xls", ".xlsm", ".xlsb"}
CSV_SUFFIXES   = {".csv", ".txt"}

def _read_csv_smart(p: Path, **kwargs) -> pd.DataFrame:
    """
    Lecture CSV robuste :
    - Détection du séparateur via csv.Sniffer (fallback , puis ;)
    - Encodage UTF-8 puis fallback cp1252
    """
    # 1) Détection séparateur (petit échantillon)
    sep = kwargs.pop("sep", None)
    if sep is None:
        try:
            sample = p.read_bytes()[:2048].decode("utf-8", errors="ignore")
            dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t,")
            sep = dialect.delimiter or ","
        except Exception:
            sep = ","  # fallback

    # 2) Encodage
    encodings = [kwargs.pop("encoding", None), "utf-8", "cp1252"]
    for enc in encodings:
        try:
            return pd.read_csv(p, sep=sep, encoding=enc, **kwargs)
        except UnicodeDecodeError:
            continue
    # Dernier essai sans encoding explicite
    return pd.read_csv(p, sep=sep, **kwargs)

def read_table(path: str | Path, **kwargs) -> pd.DataFrame:
    """
    Routeur : Excel -> read_excel ; CSV/TXT -> _read_csv_smart
    """
    p = Path(path)
    assert p.exists(), f"Fichier introuvable: {p}"
    suf = p.suffix.lower()

    if suf in EXCEL_SUFFIXES:
        return pd.read_excel(p, engine="openpyxl", **kwargs)
    if suf in CSV_SUFFIXES:
        return _read_csv_smart(p, **kwargs)
    raise ValueError(f"Extension non supportée: {p.name}")

# Aliases (si du code appelle encore ces noms)
def read_csv(path: str | Path, **kwargs) -> pd.DataFrame:
    return _read_csv_smart(Path(path), **kwargs)

def read_excel(path: str | Path, **kwargs) -> pd.DataFrame:
    return pd.read_excel(Path(path), engine="openpyxl", **kwargs)
