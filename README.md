# beishenov.com

Static mirror of Erkin Beishenov's portfolio (https://beishenov.com), originally built on
Adobe Portfolio. Everything needed to serve it is in this repo — HTML, CSS, JS and all images.

The companion site for my father's work, https://asanaly.beishenov.com, lives in its own repo
([beishenov/asanaly.beishenov.com](https://github.com/beishenov/asanaly.beishenov.com)) because
GitHub Pages allows one custom domain per repo. The mirror script and shared runtime in
`scripts/` here generate both.

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

scripts/mirror.py              Re-crawls a live site and regenerates a static copy
scripts/runtime/site.{js,css}  Source of the shared runtime (edit here, then re-run mirror)
```

The runtime replaces Adobe's bundle: hamburger nav, photo-grid reveal, image lightbox
(with captions), and a contact form that opens the visitor's mail client (Adobe's form
backend is gone — swap in Formspree or similar if you want server-side delivery).

All URLs are relative, so you can simply double-click [index.html](index.html) to view the
site — no server needed. The same files deploy unchanged to GitHub Pages, Netlify,
Cloudflare Pages, S3, or any plain web host.

## Regenerating from the live sites

```sh
python3 scripts/mirror.py                                   # beishenov.com → this repo
python3 scripts/mirror.py https://asanaly.beishenov.com ../asanaly.beishenov.com
```

Requires only the Python standard library. It downloads every page and asset,
drops the Adobe Portfolio runtime, promotes lazy-loaded images to real `src`/`srcset`,
and rewrites all CDN links to relative `assets/img/` paths.

## Notes

- Fonts are loaded from Adobe Typekit; each kit is restricted to its own domain, so on
  other hosts the browser falls back to system fonts. Replace the Typekit `<script>` in
  each page's `<head>` if you want self-hosted fonts.
- Two project pages embed Adobe XD prototypes and one embeds an Adobe video player via
  `<iframe>`; those remain remote.
- The resume link points to Dropbox.
