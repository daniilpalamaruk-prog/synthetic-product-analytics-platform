from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from .config import PROFILES, GeneratorConfig
from .generator import generate
from .settings import deep_get, load_model


def boolean(value: str) -> bool:
    value = value.lower()
    if value in {"true", "1", "yes", "y"}: return True
    if value in {"false", "0", "no", "n"}: return False
    raise argparse.ArgumentTypeError("expected true or false")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate a synthetic B2C SaaS analytics dataset")
    p.add_argument("--config-dir", type=Path, default=Path("config"))
    p.add_argument("--profile", choices=PROFILES, help="Volume preset; explicit values override it")
    p.add_argument("--users", type=int)
    p.add_argument("--target-events", type=int)
    p.add_argument("--seed", type=int)
    p.add_argument("--output", type=Path, default=Path("data"))
    p.add_argument("--chunk-size", type=int, help="Maximum buffered fact rows")
    p.add_argument("--months", type=int)
    p.add_argument("--start-date")
    p.add_argument("--gross-margin", type=float)
    p.add_argument("--inject-data-quality-issues", type=boolean)
    p.add_argument("--csv-sample", type=boolean)
    return p


def main() -> None:
    args = parser().parse_args()
    model = load_model(args.config_dir)
    defaults = deep_get(model, "defaults", {})
    profile_name = args.profile or "small"
    configured_profile = deep_get(model, f"profiles.{profile_name}")
    preset = ((configured_profile["users"], configured_profile["target_events"])
              if configured_profile else PROFILES[profile_name])
    start = datetime.fromisoformat(args.start_date or str(defaults.get("start_date", "2025-01-01"))).replace(tzinfo=timezone.utc)
    config = GeneratorConfig(
        users=args.users or preset[0], target_events=args.target_events or preset[1],
        seed=args.seed if args.seed is not None else int(defaults.get("seed", 42)), output=args.output,
        chunk_size=args.chunk_size or int(defaults.get("chunk_size", 250_000)),
        months=args.months or int(defaults.get("months", 12)), start_date=start,
        inject_data_quality_issues=(args.inject_data_quality_issues if args.inject_data_quality_issues is not None
                                    else bool(defaults.get("inject_data_quality_issues", True))),
        gross_margin=(args.gross_margin if args.gross_margin is not None else float(defaults.get("gross_margin", 0.78))),
        csv_sample=args.csv_sample if args.csv_sample is not None else bool(defaults.get("csv_sample", False)),
        model=model,
    )
    config.validate()
    manifest = generate(config)
    print(f"Generated {manifest['totals']['users']:,} users and {manifest['totals']['events']:,} events")
    print(f"Manifest: {config.output / 'manifest.json'}")
