# tests/conftest.py

import pytest
import yaml
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# ==========================================
# OPTIONS PYTEST CUSTOM
# ==========================================

def pytest_addoption(parser):
    """Ajoute l'option --QT pour activer les tests du robot QT."""
    parser.addoption(
        "--QT",
        action="store_true",
        default=False,
        help="Active les tests dépendant du robot QT (skippés par défaut)."
    )

def pytest_configure(config):
    """Enregistre le marqueur 'qt' pour éviter les warnings."""
    config.addinivalue_line(
        "markers", "qt: tests dépendant du robot QT (skippés sans --QT)"
    )

def pytest_collection_modifyitems(config, items):
    """Skip automatiquement les tests marqués @pytest.mark.qt sauf si --QT est passé."""
    if config.getoption("--QT"):
        return  # --QT activé, on ne skip rien
    
    skip_qt = pytest.mark.skip(reason="Nécessite --QT pour être exécuté (dépend du robot)")
    for item in items:
        if "qt" in item.keywords:
            item.add_marker(skip_qt)

# ==========================================
# FIXTURES GLOBALES
# ==========================================

@pytest.fixture(scope="session")
def config():
    """Charge la configuration depuis config/config.yaml"""
    config_file = PROJECT_ROOT / "config" / "config.yaml"
    assert config_file.exists(), f"Fichier config introuvable: {config_file}"
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="session")
def setup_output_dir(config):
    """Crée et retourne le dossier de sortie pour les tests."""
    output_dir = PROJECT_ROOT / config['testing']['output_dir']
    output_dir.mkdir(parents=True, exist_ok=True)
    yield str(output_dir)

@pytest.fixture(scope="session")
def qt_enabled(request):
    """Retourne True si --QT est passé en argument."""
    return request.config.getoption("--QT")
