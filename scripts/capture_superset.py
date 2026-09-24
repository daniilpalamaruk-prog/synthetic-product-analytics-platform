"""Capture the five provisioned Superset dashboards with an installed browser."""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DASHBOARDS = {
    "executive-dashboard": "executive_dashboard.png",
    "retention-dashboard": "retention_dashboard.png",
    "experiment-dashboard": "experiment_dashboard.png",
    "acquisition-dashboard": "acquisition_dashboard.png",
    "incident-dashboard": "incident_dashboard.png",
}


def local_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def browser_path() -> Path:
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    override = os.environ.get("BROWSER_EXECUTABLE")
    if override:
        candidates.insert(0, Path(override))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Chrome or Edge was not found; set BROWSER_EXECUTABLE")


def main() -> None:
    env = local_env()
    output_dir = ROOT / "docs" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    base_url = os.environ.get("SUPERSET_URL", "http://127.0.0.1:8088")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=str(browser_path()),
            headless=True,
            args=["--no-first-run", "--disable-features=msEdgeFirstRunExperience"],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
        page.goto(f"{base_url}/login/", wait_until="domcontentloaded")
        page.locator('input[name="username"]').fill(env.get("SUPERSET_ADMIN_USER", "admin"))
        page.locator('input[name="password"]').fill(env["SUPERSET_ADMIN_PASSWORD"])
        page.locator('input[type="submit"], button[type="submit"]').first.click()
        page.wait_for_url(lambda url: "/login/" not in url, timeout=30_000)

        for slug, filename in DASHBOARDS.items():
            page.goto(f"{base_url}/superset/dashboard/{slug}/", wait_until="domcontentloaded")
            page.wait_for_selector(".dashboard-content, .dashboard", timeout=30_000)
            page.wait_for_timeout(8_000)
            error_text = page.locator(
                ".chart-container .alert, .alert-danger, .ant-alert-error, [role='alert']"
            ).all_inner_texts()
            if error_text:
                raise RuntimeError(f"Dashboard {slug} contains chart errors: {error_text}")
            page.screenshot(path=str(output_dir / filename), full_page=True)
            print(f"Captured {filename}")
        browser.close()


if __name__ == "__main__":
    main()
