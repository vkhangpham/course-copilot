from pathlib import Path

from apps.codeact.tools.data import load_dataset_asset

DATASET_DIR = Path("data/handcrafted/database_systems")


def test_load_dataset_asset_json() -> None:
    asset = load_dataset_asset("quiz_bank.json", base_dir=DATASET_DIR)
    assert isinstance(asset, list)
    assert asset, "Expected quiz bank entries"


def test_load_dataset_asset_yaml() -> None:
    asset = load_dataset_asset("taxonomy.yaml", base_dir=DATASET_DIR)
    assert isinstance(asset, dict)
    assert "domains" in asset
