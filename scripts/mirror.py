#!/usr/bin/env python3
"""Mirror an Adobe Portfolio site into a self-contained static site.

Crawls the live site, downloads every CDN image and stylesheet, strips the
Adobe Portfolio runtime, and rewrites the HTML so it works from any static host.

Usage:
  python3 scripts/mirror.py                                   # beishenov.com -> repo root
  python3 scripts/mirror.py https://asanaly.beishenov.com ../asanaly.beishenov.com
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"

# Set from CLI args in main()
SITE = "https://beishenov.com"
ROOT = REPO
IMG_DIR = ROOT / "assets" / "img"
CSS_DIR = ROOT / "assets" / "css"
PAGE_ALIASES: dict[str, str] = {}  # e.g. {"/projects": "/"} when canonical home differs

UA = {"User-Agent": "Mozilla/5.0 (site-mirror; +https://beishenov.com)"}

CDN_RE = re.compile(r"https://[a-z0-9.-]*myportfolio\.com/[^\s\"'<>,)]+")
THEME_CSS_RE = re.compile(r'href="(https://[a-z0-9.-]*myportfolio\.com/[^"]+\.css[^"]*)"')
INTERNAL_LINK_RE = re.compile(r'href="(/[a-z0-9][a-z0-9-]*)"')
CANONICAL_RE = re.compile(r'rel="canonical" href="https?://[^/"]+(/[^"]*)"')


def fetch(url: str, retries: int = 3) -> bytes:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise
            print(f"  retry {attempt + 1} for {url}: {exc}", file=sys.stderr)
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def local_image_name(cdn_url: str) -> str:
    path = urllib.parse.urlparse(cdn_url).path
    return os.path.basename(path)


def download_asset(cdn_url: str) -> None:
    dest = IMG_DIR / local_image_name(cdn_url)
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.write_bytes(fetch(cdn_url))


# --------------------------------------------------------------------------- #
# HTML rewriting
# --------------------------------------------------------------------------- #

def _rewrite_img(match: re.Match) -> str:
    """Promote lazy-load data-* attributes to real attributes on an <img>."""
    tag = match.group(0)
    if "data-src=" not in tag:
        return tag
    tag = re.sub(r'\ssrc="[^"]*"', "", tag)  # drop 1px gif / tiny placeholder
    tag = tag.replace("data-src=", "src=")
    tag = tag.replace("data-srcset=", "srcset=")
    tag = tag.replace("data-sizes=", "sizes=")
    tag = re.sub(r'\sheight="0"', "", tag)
    tag = re.sub(r'\sstyle="padding-bottom:\s*[\d.]+%;\s*background:[^"]*"', "", tag)
    tag = re.sub(r'srcset="([^"]*?),\s*"', r'srcset="\1"', tag)  # trailing comma
    tag = tag.replace("js-lazy", "js-lazy image-loaded", 1)
    tag = tag.replace("<img", '<img loading="lazy"', 1)
    return tag


def rewrite_html(html: str, theme_css: dict[str, str]) -> str:
    # Stylesheets (each Adobe Portfolio page ships its own theme CSS build)
    html = html.replace('href="/dist/css/main.css"', 'href="/assets/css/main.css"')
    for url, local in theme_css.items():
        html = html.replace(f'href="{url}"', f'href="{local}"')
    html = re.sub(
        r'(<link rel="stylesheet" href="/assets/css/theme[^"]*\.css" type="text/css" />)',
        r'\1\n      <link rel="stylesheet" href="/assets/css/site.css" type="text/css" />',
        html,
        count=1,
    )

    # Remove Adobe Portfolio runtime (config, translations, main.js, bfcache hack)
    html = re.sub(r"\s*<script[^>]*>\s*// fix for Safari's back/forward cache.*?</script>", "", html, flags=re.S)
    html = re.sub(r"\s*<script[^>]*>var __config__ = .*?</script>", "", html, flags=re.S)
    html = re.sub(r'\s*<script[^>]*src="/site/translations[^"]*"></script>', "", html)
    html = re.sub(r'\s*<script[^>]*src="/dist/js/main\.js[^"]*"></script>', "", html)
    html = html.replace("</body>", '  <script src="/assets/js/site.js" defer></script>\n</body>')

    # Body is hidden until the runtime reveals it; reveal statically.
    html = html.replace('<body class="transition-enabled">', "<body>")

    # Protocol-relative URLs break under file://
    html = html.replace('src="//use.typekit.net/', 'src="https://use.typekit.net/')

    # Lazy images -> eager images
    html = re.sub(r"<img\b[^>]*>", _rewrite_img, html, flags=re.S)

    # Editor leftovers that have no meaning outside Adobe Portfolio
    html = re.sub(r'\s(?:contenteditable|decorator|data-text-keypath|data-hover-hint(?:-id)?|data-context|data-identity)="[^"]*"', "", html)
    html = re.sub(r'\svalue="[^"]*"', lambda m: m.group(0) if "<input" in m.group(0) else "", html)

    # CDN assets -> local
    html = CDN_RE.sub(lambda m: "/assets/img/" + local_image_name(m.group(0)), html)

    # Canonical URLs: the home gallery's alias slug should point at the root
    for alias in PAGE_ALIASES:
        html = html.replace(f'rel="canonical" href="{SITE}{alias}"', f'rel="canonical" href="{SITE}/"')

    return html


def rewrite_css(css: str) -> str:
    # CSS lives in assets/css/, so images are a sibling folder away
    return CDN_RE.sub(lambda m: "../img/" + local_image_name(m.group(0)), css)


def relativize(html: str, depth: int, page_paths: set[str]) -> str:
    """Turn root-relative URLs into relative ones so the page works from file://.

    depth is how many folders below the site root the page lives in.
    """
    prefix = "../" * depth

    # Social previews need absolute URLs; everything else goes relative.
    html = re.sub(r'(property="og:image"\s+content=")/assets/', rf'\1{SITE}/assets/', html)
    html = re.sub(r'(?<=["\',(\s])/assets/', f"{prefix}assets/", html)

    def _link(m: re.Match) -> str:
        path = m.group(1)
        if path == "/":
            return f'href="{prefix}index.html"'
        if path in page_paths:
            return f'href="{prefix}{path.lstrip("/")}/index.html"'
        return m.group(0)

    html = re.sub(r'href="(/[a-z0-9-]*)"', _link, html)
    return html


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    global SITE, ROOT, IMG_DIR, CSS_DIR, PAGE_ALIASES

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("site", nargs="?", default=SITE, help="site origin, e.g. https://beishenov.com")
    ap.add_argument("out", nargs="?", default=".", help="output directory (relative to the repo root, or absolute)")
    args = ap.parse_args()

    SITE = args.site.rstrip("/")
    ROOT = (REPO / args.out).resolve()
    IMG_DIR = ROOT / "assets" / "img"
    CSS_DIR = ROOT / "assets" / "css"
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    CSS_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "assets" / "js").mkdir(parents=True, exist_ok=True)

    print(f"Mirroring {SITE} -> {ROOT}")
    print("Fetching home page…")
    home = fetch(SITE + "/").decode("utf-8")

    # Adobe Portfolio serves the home gallery under its own slug too (e.g. /projects).
    canonical = CANONICAL_RE.search(home)
    if canonical and canonical.group(1) not in ("/", ""):
        PAGE_ALIASES = {canonical.group(1).rstrip("/"): "/"}

    # Discover pages (one level is enough for Adobe Portfolio galleries,
    # but we crawl until no new internal links appear).
    pages: dict[str, str] = {"/": home}
    queue = list(dict.fromkeys(p for p in INTERNAL_LINK_RE.findall(home) if p not in PAGE_ALIASES))
    seen = set(queue) | {"/"}
    while queue:
        path = queue.pop(0)
        print(f"Fetching {path}…")
        html = fetch(SITE + path).decode("utf-8")
        pages[path] = html
        for link in INTERNAL_LINK_RE.findall(html):
            if link not in seen and link not in PAGE_ALIASES:
                seen.add(link)
                queue.append(link)

    print("Fetching stylesheets…")
    main_css = fetch(SITE + "/dist/css/main.css").decode("utf-8")

    # Every page references its own theme CSS build; most are byte-identical.
    theme_urls: list[str] = []
    for html in pages.values():
        for url in THEME_CSS_RE.findall(html):
            if url not in theme_urls:
                theme_urls.append(url)
    home_theme_url = THEME_CSS_RE.search(home).group(1)
    theme_urls.remove(home_theme_url)
    theme_urls.insert(0, home_theme_url)

    theme_css: dict[str, str] = {}  # cdn url -> local href
    theme_bodies: dict[str, str] = {}  # local href -> css
    by_digest: dict[str, str] = {}
    for i, url in enumerate(theme_urls):
        css = fetch(url).decode("utf-8")
        digest = hashlib.sha256(css.encode("utf-8")).hexdigest()
        if digest not in by_digest:
            local = "/assets/css/theme.css" if i == 0 else f"/assets/css/theme-{len(by_digest)}.css"
            by_digest[digest] = local
            theme_bodies[local] = css
        theme_css[url] = by_digest[digest]
    print(f"  {len(theme_urls)} theme stylesheets, {len(theme_bodies)} unique")

    # Collect every CDN asset referenced anywhere
    assets: set[str] = set()
    for html in pages.values():
        assets.update(CDN_RE.findall(html))
    for css in theme_bodies.values():
        assets.update(CDN_RE.findall(css))
    assets = {a for a in assets if not a.split("?")[0].endswith(".css")}

    print(f"Downloading {len(assets)} assets…")
    failed: list[str] = []

    def _dl(url: str) -> None:
        try:
            download_asset(url)
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{url}: {exc}")

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(_dl, sorted(assets)))
    if failed:
        print("Failed downloads:", file=sys.stderr)
        for f in failed:
            print("  " + f, file=sys.stderr)

    print("Writing stylesheets…")
    (CSS_DIR / "main.css").write_text(rewrite_css(main_css), encoding="utf-8")
    for local, css in theme_bodies.items():
        (ROOT / local.lstrip("/")).write_text(rewrite_css(css), encoding="utf-8")
    shutil.copy(RUNTIME_DIR / "site.css", CSS_DIR / "site.css")
    shutil.copy(RUNTIME_DIR / "site.js", ROOT / "assets" / "js" / "site.js")

    print("Writing pages…")
    page_paths = set(pages) | set(PAGE_ALIASES)
    for path, html in pages.items():
        depth = 0 if path == "/" else 1
        out = relativize(rewrite_html(html, theme_css), depth, page_paths)
        dest = ROOT / "index.html" if path == "/" else ROOT / path.lstrip("/") / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(out, encoding="utf-8")
        print(f"  {dest.relative_to(ROOT)}")
    for alias, target in PAGE_ALIASES.items():
        dest = ROOT / alias.lstrip("/") / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(relativize(rewrite_html(pages[target], theme_css), 1, page_paths), encoding="utf-8")
        print(f"  {dest.relative_to(ROOT)} (alias of {target})")

    print(f"Done. {len(pages)} pages, {len(assets) - len(failed)} assets.")


if __name__ == "__main__":
    main()
