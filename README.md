# beishenov.com

Static mirrors of two Adobe Portfolio sites. Everything needed to serve them is in this
repo — HTML, CSS, JS and all images.

| Site | Folder (web root) | Pages |
|------|-------------------|-------|
| https://beishenov.com — Erkin Beishenov, product design portfolio | repo root | home + 9 case studies |
| https://asanaly.beishenov.com — Бейшенов Асаналы, artist portfolio | `asanaly/` | galleries, about, contact |

Each folder is a self-contained site with its own `assets/`; deploy them to their
respective domains as separate web roots.

## Structure

```
index.html                     Home (gallery of projects)
projects/index.html            Alias of the home page
<project-slug>/index.html      One folder per case study (9 projects)
assets/css/main.css            Adobe Portfolio base styles
assets/css/theme*.css          Per-page theme builds exported by Adobe Portfolio
assets/css/site.css            Local additions (lightbox)  ← copied from scripts/runtime/
assets/js/site.js              Minimal runtime                ← copied from scripts/runtime/
assets/img/                    All images (every responsive variant)

asanaly/                       Same layout for asanaly.beishenov.com
  index.html, gallery/ (alias), knmii/, personal/, the-state-tretyakov-gallery/,
  o-khudozhnike/, contact/, assets/

scripts/mirror.py              Re-crawls a live site and regenerates a folder above
scripts/runtime/site.{js,css}  Source of the shared runtime (edit here, then re-run mirror)
```

The runtime replaces Adobe's bundle: hamburger nav, photo-grid reveal, image lightbox
(with captions), and a contact form that opens the visitor's mail client (Adobe's form
backend is gone — swap in Formspree or similar if you want server-side delivery).

All URLs are relative, so you can simply double-click any `index.html` to view a site
— no server needed. The same files deploy unchanged to GitHub Pages, Netlify,
Cloudflare Pages, S3, or any plain web host.

- Your portfolio: open [index.html](index.html)
- Father's portfolio: open [asanaly/index.html](asanaly/index.html)

## Regenerating from the live sites

```sh
python3 scripts/mirror.py                                   # beishenov.com → repo root
python3 scripts/mirror.py https://asanaly.beishenov.com asanaly
```

Requires only the Python standard library. It downloads every page and asset,
drops the Adobe Portfolio runtime, promotes lazy-loaded images to real `src`/`srcset`,
and rewrites all CDN links to `/assets/img/`.

## Notes

- Fonts are loaded from Adobe Typekit; each kit is restricted to its own domain, so on
  other hosts the browser falls back to system fonts. Replace the Typekit `<script>` in
  each page's `<head>` if you want self-hosted fonts.
- Two project pages embed Adobe XD prototypes and one embeds an Adobe video player via
  `<iframe>`; those remain remote.
- The resume link points to Dropbox.
