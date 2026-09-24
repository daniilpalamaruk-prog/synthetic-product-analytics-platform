from pathlib import Path

from scripts.bootstrap_env import main


def test_bootstrap_env_replaces_all_secret_placeholders(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(".env.example").write_text(
        "PII_HMAC_SECRET=replace-with-at-least-16-random-bytes\n"
        "PII_ENCRYPTION_KEY=replace-with-a-fernet-key\n"
        "POSTGRES_PASSWORD=replace-local-postgres-password\n",
        encoding="utf-8",
    )
    main()
    result = Path(".env").read_text(encoding="utf-8")
    assert "replace-" not in result
    assert len(result.splitlines()) == 3
