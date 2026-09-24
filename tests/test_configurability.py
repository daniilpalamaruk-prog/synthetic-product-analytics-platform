import copy
import json
from pathlib import Path

import pyarrow.dataset as ds

from saasgen.config import GeneratorConfig
from saasgen.generator import generate
from saasgen.settings import load_model, model_hash


def test_yaml_rules_change_generated_behavior(tmp_path: Path):
    model = copy.deepcopy(load_model(Path("config")))
    model["platform_distribution"] = {"web": 1.0, "ios": 0.0, "android": 0.0}
    model["plans"]["basic_price"] = 99.0
    model["plans"]["new_pricing_basic_price"] = 101.0
    config = GeneratorConfig(users=500, target_events=10_000, seed=77, output=tmp_path,
                             chunk_size=5000, inject_data_quality_issues=False, model=model)
    manifest = generate(config)
    users = ds.dataset(tmp_path / "clean/users", format="parquet").to_table(columns=["device_type"])
    assert set(users["device_type"].to_pylist()) == {"web"}
    subscriptions = ds.dataset(tmp_path / "clean/subscriptions", format="parquet").to_table().to_pylist()
    basic_prices = {float(r["monthly_price_usd"]) for r in subscriptions if r["plan"] == "basic"}
    assert basic_prices and basic_prices <= {99.0, 101.0}
    assert manifest["model_config_hash"] == model_hash(model)
    persisted = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert persisted["model_config"]["plans"]["basic_price"] == 99.0
