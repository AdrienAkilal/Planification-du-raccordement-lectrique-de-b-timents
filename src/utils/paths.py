# src/utils/paths.py
from pathlib import Path
from datetime import datetime


def root_dir() -> Path:
    """Retourne la racine du projet."""
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Dossier data/"""
    return root_dir() / "data"


def staging_dir() -> Path:
    """Dossier staging/ (avec sous-dossier horodaté)."""
    d = data_dir() / "staging"
    d.mkdir(parents=True, exist_ok=True)
    return d


def outputs_dir() -> Path:
    """Dossier outputs/ (avec sous-dossier horodaté)."""
    d = data_dir() / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def timestamped_path(base: str, ext: str = "csv") -> Path:
    """
    Crée un chemin du type:
      data/outputs/base_2025-10-31T22-50-30.csv
    """
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    d = outputs_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{base}_{ts}.{ext}"
