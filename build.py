#!/usr/bin/env python3
"""Build Suno from one template into two shapes.

  suno.html   a single self-contained file (Claude Artifact / email / USB stick)
  docs/       a plain static site for GitHub Pages
"""
import base64, pathlib, shutil, sys

root = pathlib.Path(__file__).parent
build = root / "node_modules/pdfjs-dist/legacy/build"
tpl = (root / "template.html").read_text(encoding="utf-8")

lib_src = (build / "pdf.min.js").read_text(encoding="utf-8")
for bad in ("</script", "<!--"):
    if bad in lib_src:
        sys.exit("pdf.min.js contains %r; cannot inline verbatim" % bad)

assert "/*__PDFJS__*/" in tpl and "/*__WORKER_SETUP__*/" in tpl

# --------------------------------------------------------------- single file
INLINE_WORKER = '''/* ------------------------------------------------------------------ *
 * pdf.js worker: embedded as base64 and turned into a blob URL, so this
 * one file needs no network at all.
 * ------------------------------------------------------------------ */
var WORKER_B64 = "%s";
try {
  var bin = atob(WORKER_B64), n = bin.length, bytes = new Uint8Array(n);
  for (var wi = 0; wi < n; wi++) bytes[wi] = bin.charCodeAt(wi);
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    URL.createObjectURL(new Blob([bytes], {type: "text/javascript"}));
} catch (e) {
  console.error("worker setup failed", e);
}'''

worker_b64 = base64.b64encode((build / "pdf.worker.min.js").read_bytes()).decode("ascii")
single = tpl.replace("/*__PDFJS__*/", lib_src)
single = single.replace("/*__WORKER_SETUP__*/", INLINE_WORKER % worker_b64)
(root / "suno.html").write_text(single, encoding="utf-8")

# --------------------------------------------------------------- static site
FILE_WORKER = '''/* pdf.js does its parsing in a worker; it is served next to this page. */
pdfjsLib.GlobalWorkerOptions.workerSrc = "pdf.worker.min.js";'''

HEAD_EXTRA = '''<meta charset="utf-8">
<meta name="description" content="Turn a Hindi PDF into an audiobook. Reads each page aloud in your device's own Hindi voice, highlighting the sentence being spoken.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png" sizes="192x192">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Suno">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0F1218">
'''

site = tpl.replace('<script>/*__PDFJS__*/</script>', '<script src="pdf.min.js"></script>')
site = site.replace("/*__WORKER_SETUP__*/", FILE_WORKER)

# The template is authored as a fragment (the Artifact host supplies the
# skeleton); a real site needs the whole document.
title_line = "<title>Suno Hindi Reader</title>\n"
assert site.startswith(title_line)
site = site[len(title_line):]
cut = site.index("</style>") + len("</style>")
doc = ("<!doctype html>\n<html lang=\"hi\">\n<head>\n" + HEAD_EXTRA + title_line
       + site[:cut].strip() + "\n</head>\n<body>\n"
       + site[cut:].strip() + "\n</body>\n</html>\n")

MANIFEST = """{
  "name": "Suno Hindi Reader",
  "short_name": "Suno",
  "description": "Turn a Hindi PDF into an audiobook, read aloud page by page.",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#EFEEE8",
  "theme_color": "#EFEEE8",
  "lang": "hi",
  "dir": "ltr",
  "categories": ["books", "education", "utilities"],
  "icons": [
    { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
"""

docs = root / "docs"
docs.mkdir(exist_ok=True)
(docs / "index.html").write_text(doc, encoding="utf-8")
(docs / "manifest.webmanifest").write_text(MANIFEST, encoding="utf-8")
shutil.copy(build / "pdf.min.js", docs / "pdf.min.js")
shutil.copy(build / "pdf.worker.min.js", docs / "pdf.worker.min.js")
for icon in ("icon-192.png", "icon-512.png", "icon-maskable-512.png",
             "apple-touch-icon.png", "favicon-32.png"):
    shutil.copy(root / "assets" / icon, docs / icon)
# GitHub Pages runs Jekyll by default, which would ignore nothing here but
# adds a needless build step; this switches it off.
(docs / ".nojekyll").write_text("", encoding="utf-8")

print("suno.html        %.2f MB" % ((root / "suno.html").stat().st_size / 1048576))
for f in sorted(docs.iterdir()):
    print("docs/%-22s %7.1f KB" % (f.name, f.stat().st_size / 1024))
