"""Build a five-second README demo GIF from the running local stack.

Requires Playwright and Pillow in addition to the project dependencies.
Superset screenshots must already exist under docs/images.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from capture_superset import browser_path, local_env
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "demo.gif"
SIZE = (1200, 675)
FRAMES_PER_SCENE = 5
FRAME_DURATION_MS = 250


def capture_airflow(page: Page, env: dict[str, str], target: Path) -> None:
    base_url = os.environ.get("AIRFLOW_URL", "http://127.0.0.1:8081")
    page.goto(f"{base_url}/login/", wait_until="domcontentloaded")
    page.locator('input[name="username"]').fill(env.get("AIRFLOW_ADMIN_USER", "admin"))
    page.locator('input[name="password"]').fill(env["AIRFLOW_ADMIN_PASSWORD"])
    page.locator('input[type="submit"], button[type="submit"]').first.click()
    page.wait_for_url(lambda url: "/login/" not in url, timeout=30_000)
    page.goto(
        f"{base_url}/dags/build_analytics_marts/grid",
        wait_until="domcontentloaded",
    )
    page.wait_for_selector("body", timeout=30_000)
    page.wait_for_timeout(5_000)
    if "/login/" in page.url:
        raise RuntimeError("Airflow authentication failed")
    page.screenshot(path=str(target), full_page=False)


def capture_benchmark(page: Page, target: Path) -> None:
    url = (
        "https://github.com/daniilpalamaruk-prog/"
        "synthetic-product-analytics-platform/blob/main/"
        "benchmarks/results/greenplum_query_optimization.md"
    )
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    report = page.locator("article.markdown-body")
    report.wait_for(timeout=30_000)
    results = report.get_by_role("heading", name="Results", exact=True)
    results.scroll_into_view_if_needed()
    page.evaluate("window.scrollBy(0, -110)")
    page.wait_for_timeout(1_500)
    page.screenshot(path=str(target), full_page=False)


def cover(image: Image.Image, size: tuple[int, int], zoom: float) -> Image.Image:
    target_width, target_height = size
    scale = max(target_width / image.width, target_height / image.height) * zoom
    resized = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = max(0, (resized.width - target_width) // 2)
    top = max(0, (resized.height - target_height) // 2)
    return resized.crop((left, top, left + target_width, top + target_height))


def font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / name
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def render_frame(
    source: Path,
    eyebrow: str,
    title: str,
    scene_index: int,
    progress: int,
) -> Image.Image:
    with Image.open(source) as original:
        frame = cover(original.convert("RGB"), SIZE, 1 + progress * 0.003)

    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((26, 24, 590, 116), radius=14, fill=(15, 23, 42, 224))
    draw.text((48, 38), eyebrow, font=font("segoeuib.ttf", 19), fill=(56, 189, 248, 255))
    draw.text((48, 67), title, font=font("segoeuib.ttf", 31), fill=(255, 255, 255, 255))

    bar_y = SIZE[1] - 12
    draw.rectangle((0, bar_y, SIZE[0], SIZE[1]), fill=(15, 23, 42, 210))
    completed = ((scene_index * FRAMES_PER_SCENE + progress + 1) / (4 * FRAMES_PER_SCENE))
    draw.rectangle((0, bar_y, round(SIZE[0] * completed), SIZE[1]), fill=(56, 189, 248, 255))
    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def main() -> None:
    env = local_env()
    with tempfile.TemporaryDirectory(prefix="synthetic-saas-demo-") as temp:
        temp_dir = Path(temp)
        airflow = temp_dir / "airflow.png"
        benchmark = temp_dir / "benchmark.png"

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=str(browser_path()),
                headless=True,
                args=["--no-first-run", "--disable-features=msEdgeFirstRunExperience"],
            )
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            capture_airflow(page, env, airflow)
            capture_benchmark(page, benchmark)
            browser.close()

        scenes = [
            (
                ROOT / "docs" / "images" / "executive_dashboard.png",
                "01  SUPERSET",
                "Executive dashboard",
            ),
            (
                ROOT / "docs" / "images" / "retention_dashboard.png",
                "02  SUPERSET",
                "Retention cohorts",
            ),
            (airflow, "03  AIRFLOW", "Analytics marts DAG"),
            (benchmark, "04  GREENPLUM", "Query optimization: 9.82×"),
        ]

        frames = [
            render_frame(source, eyebrow, title, scene_index, progress)
            for scene_index, (source, eyebrow, title) in enumerate(scenes)
            for progress in range(FRAMES_PER_SCENE)
        ]
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(
            OUTPUT,
            save_all=True,
            append_images=frames[1:],
            duration=FRAME_DURATION_MS,
            loop=0,
            optimize=True,
        )
        print(
            f"Created {OUTPUT.relative_to(ROOT)}: "
            f"{len(frames)} frames, "
            f"{len(frames) * FRAME_DURATION_MS / 1000:.1f} seconds"
        )


if __name__ == "__main__":
    main()
