"""Capture ONLY real running local UI; no fabricated device/API result images."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def capture(url, output):
    with sync_playwright() as p:
        candidates = [Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
                      Path("C:/Program Files/Google/Chrome/Application/chrome.exe")]
        executable = next((str(x) for x in candidates if x.exists()), None)
        browser = p.chromium.launch(headless=True, executable_path=executable)
        page = browser.new_page(viewport={"width": 1600, "height": 1080}, device_scale_factor=1)
        # Gradio can keep background network connections open; wait for visible UI instead.
        page.goto(url, wait_until="domcontentloaded")
        page.get_by_role("heading", name="HomeManager 智能家居管家 Agent", exact=True).wait_for()
        page.screenshot(path=str(output), full_page=True)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:7860")
    parser.add_argument("--output", type=Path, default=ROOT/"results/screenshots/gradio_initial.png")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    capture(args.url, args.output)
    print(args.output)
