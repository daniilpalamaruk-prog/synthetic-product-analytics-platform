"""Create an ignored local .env with cryptographically random development secrets."""

from __future__ import annotations

import secrets
from pathlib import Path

from cryptography.fernet import Fernet


def main() -> None:
    target = Path(".env")
    if target.exists():
        print(".env already exists; leaving it unchanged")
        return
    template = Path(".env.example").read_text(encoding="utf-8")
    replacements = {
        "replace-with-at-least-16-random-bytes": secrets.token_urlsafe(32),
        "replace-with-a-fernet-key": Fernet.generate_key().decode("ascii"),
        "replace-local-airflow-password": secrets.token_urlsafe(24),
        "replace-local-postgres-password": secrets.token_urlsafe(24),
        "replace-local-greenplum-password": secrets.token_urlsafe(24),
        "replace-with-at-least-32-random-bytes": secrets.token_urlsafe(48),
        "replace-local-superset-password": secrets.token_urlsafe(24),
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    target.write_text(template, encoding="utf-8")
    print("Created ignored local .env with random development secrets")


if __name__ == "__main__":
    main()
