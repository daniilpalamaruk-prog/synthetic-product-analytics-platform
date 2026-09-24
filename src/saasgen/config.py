from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

PROFILES = {
    "small": (10_000, 400_000),
    "medium": (100_000, 7_000_000),
    "large": (1_000_000, 70_000_000),
}


@dataclass(frozen=True)
class GeneratorConfig:
    users: int
    target_events: int
    seed: int
    output: Path
    chunk_size: int = 250_000
    months: int = 12
    start_date: datetime = datetime(2025, 1, 1, tzinfo=timezone.utc)
    inject_data_quality_issues: bool = True
    gross_margin: float = 0.78
    csv_sample: bool = False
    model: dict = field(default_factory=dict, repr=False, compare=False)

    def validate(self) -> None:
        if self.users < 1:
            raise ValueError("users must be positive")
        if self.target_events < self.users * 4:
            raise ValueError("target-events must be at least 4x users")
        if self.chunk_size < 1_000:
            raise ValueError("chunk-size must be >= 1000")
        if self.months < 12:
            raise ValueError("months must be >= 12 to preserve the business story")
        if not 0.70 <= self.gross_margin <= 0.85:
            raise ValueError("gross-margin must be between 0.70 and 0.85")
