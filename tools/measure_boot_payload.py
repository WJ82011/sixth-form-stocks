#!/usr/bin/env python3
"""Print first-load script/CSS weight for index.html after lazy-load."""
import re
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"


def file_bytes(href: str) -> int:
    path = SITE / href.split("?", 1)[0].lstrip("/")
    return path.stat().st_size if path.exists() else 0


def index_scripts():
    html = (SITE / "index.html").read_text()
    return [m.group(1) for m in re.finditer(r'<script[^>]+src="([^"]+)"', html)]


def index_styles():
    html = (SITE / "index.html").read_text()
    return [m.group(1) for m in re.finditer(r'<link rel="stylesheet" href="([^"]+)"', html)]


def boot_lists():
    text = (SITE / "view-loader.js").read_text()
    boot_scripts, boot_styles = [], []
    mode = None
    for line in text.splitlines():
        if "BOOT_SCRIPTS" in line:
            mode = "scripts"
            continue
        if "BOOT_STYLES" in line:
            mode = "styles"
            continue
        if mode and line.strip().startswith("];"):
            mode = None
            continue
        if mode == "scripts" and "/" in line:
            boot_scripts.extend(re.findall(r"'(/[^']+)'", line))
        if mode == "styles" and "/" in line:
            boot_styles.extend(re.findall(r"'(/[^']+)'", line))
    return boot_scripts, boot_styles


def main():
    scripts = index_scripts()
    styles = index_styles()
    boot_scripts, boot_styles = boot_lists()
    html_js = sum(file_bytes(s) for s in scripts)
    html_css = sum(file_bytes(s) for s in styles)
    boot_js = sum(file_bytes(s) for s in boot_scripts)
    boot_css = sum(file_bytes(s) for s in boot_styles)
    app_js = file_bytes("/app.js")
    print("index.html script tags:", len(scripts), html_js, "bytes")
    print("index.html stylesheet tags:", len(styles), html_css, "bytes")
    print("view-loader boot scripts:", len(boot_scripts), boot_js, "bytes")
    print("view-loader boot styles:", len(boot_styles), boot_css, "bytes")
    print("app.js deferred:", app_js, "bytes")
    print("Estimated first-paint JS:", html_js + boot_js + app_js, "bytes")
    print("Estimated first-paint CSS:", html_css + boot_css, "bytes")


if __name__ == "__main__":
    main()