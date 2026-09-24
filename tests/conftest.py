from pathlib import Path

import pytest

from saasgen.config import GeneratorConfig
from saasgen.generator import generate
from saasgen.settings import load_model


@pytest.fixture(scope="session")
def analytical_dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("analytical_dataset")
    config = GeneratorConfig(users=6_000, target_events=240_000, seed=42, output=root,
                             chunk_size=80_000, inject_data_quality_issues=False,
                             model=load_model(Path("config")))
    generate(config)
    return root

