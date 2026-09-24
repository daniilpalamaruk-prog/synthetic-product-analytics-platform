"""Remove only known generated outputs; never traverse arbitrary user paths."""

import shutil
from pathlib import Path

TARGETS = (Path("data/small"), Path("data/acceptance"), Path("data/warehouse.db"), Path("data/acceptance.db"))
workspace = Path.cwd().resolve()
for target in TARGETS:
    resolved = target.resolve()
    if workspace not in resolved.parents:
        raise RuntimeError(f"refusing to remove path outside workspace: {resolved}")
    if resolved.is_dir():
        shutil.rmtree(resolved)
    elif resolved.exists():
        resolved.unlink()
