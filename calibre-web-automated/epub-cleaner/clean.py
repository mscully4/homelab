"""Strip piracy-site watermarks from EPUBs before Calibre-Web-Automated ingests them.

Some download sites inject a link back to themselves into every chapter and
drop a marker file into the zip. Gmail's attachment scanner flags those, which
makes CWA's Send-to-eReader fail with "552 5.7.0 ... potential security issue".

Usage:
  clean.py FILE.epub [OUT.epub]   clean one file (in place if OUT omitted)
  clean.py --watch SRC DST        move every stable book from SRC to DST,
                                  cleaning EPUBs on the way
"""

import os
import re
import shutil
import sys
import tempfile
import time
import zipfile

DOMAINS = [d.strip() for d in os.environ.get("CLEAN_DOMAINS", "oceanofpdf.com").split(",") if d.strip()]
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "2"))
TEMP_SUFFIXES = (".crdownload", ".download", ".part", ".uploading", ".tmp")
TEXT_EXTS = (".xhtml", ".html", ".htm", ".opf", ".ncx")


def _patterns():
    pats = []
    for d in DOMAINS:
        dr = re.escape(d)
        link = rf'<a\b[^>]*{dr}[^>]*>.*?</a>'
        # Whole watermark block: <div ...><p><a href=site>Site</a></p></div>
        pats.append(re.compile(rf'<div\b[^>]*>\s*<p\b[^>]*>\s*{link}\s*</p>\s*</div>', re.I | re.S))
        # Bare paragraph holding only the link
        pats.append(re.compile(rf'<p\b[^>]*>\s*{link}\s*</p>', re.I | re.S))
        # Any remaining link to the site, text and all
        pats.append(re.compile(link, re.I | re.S))
    return pats


def _move(src, dst):
    """Move src to dst so dst appears atomically, even across mounts."""
    try:
        os.replace(src, dst)
    except OSError:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(dst)), prefix=".moving-", suffix=".tmp")
        os.close(fd)
        shutil.copyfile(src, tmp)
        os.chmod(tmp, 0o644)
        os.replace(tmp, dst)
        os.remove(src)


def _is_marker(name):
    base = name.rsplit("/", 1)[-1].lower()
    return any(d.lower() in base for d in DOMAINS)


def clean_epub(src, dst=None):
    """Return number of changes made. Writes dst (or replaces src) only if something changed."""
    pats = _patterns()
    changes = 0
    out_entries = []
    with zipfile.ZipFile(src) as zin:
        removed = [i.filename for i in zin.infolist() if _is_marker(i.filename)]
        changes += len(removed)
        for info in zin.infolist():
            if info.filename in removed:
                continue
            data = zin.read(info.filename)
            if info.filename.lower().endswith(TEXT_EXTS):
                text = data.decode("utf-8", errors="surrogateescape")
                orig = text
                for p in pats:
                    text = p.sub("", text)
                # Drop manifest entries pointing at removed marker files
                for r in removed:
                    rb = re.escape(r.rsplit("/", 1)[-1])
                    text = re.sub(rf'\s*<item\b[^>]*href="[^"]*{rb}"[^>]*/>', "", text)
                if text != orig:
                    changes += 1
                    data = text.encode("utf-8", errors="surrogateescape")
            out_entries.append((info, data))

    if not changes:
        if dst and dst != src:
            _move(src, dst)
        return 0

    target = dst or src
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(target)), prefix=".cleaning-", suffix=".tmp")
    os.close(fd)
    os.chmod(tmp, os.stat(src).st_mode & 0o777 | 0o644)  # mkstemp creates 0600
    with zipfile.ZipFile(tmp, "w") as zout:
        # EPUB spec: "mimetype" must be first and stored uncompressed
        for info, data in sorted(out_entries, key=lambda e: e[0].filename != "mimetype"):
            if info.filename == "mimetype":
                zout.writestr(info, data, compress_type=zipfile.ZIP_STORED)
            else:
                zout.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    os.replace(tmp, target)
    if dst and dst != src and os.path.exists(src):
        os.remove(src)
    return changes


def watch(src_dir, dst_dir):
    print(f"[epub-cleaner] watching {src_dir} -> {dst_dir}, domains={DOMAINS}", flush=True)
    last_sizes = {}
    while True:
        seen = {}
        for root, _, files in os.walk(src_dir):
            for f in files:
                path = os.path.join(root, f)
                if f.startswith(".") or f.lower().endswith(TEMP_SUFFIXES):
                    continue
                try:
                    seen[path] = os.path.getsize(path)
                except OSError:
                    continue
        for path, size in seen.items():
            # Only act once the size has held steady across two polls
            if last_sizes.get(path) != size:
                continue
            rel = os.path.relpath(path, src_dir)
            dst = os.path.join(dst_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                if path.lower().endswith(".epub"):
                    n = clean_epub(path, dst)
                    print(f"[epub-cleaner] {rel}: {n} change(s)", flush=True)
                else:
                    _move(path, dst)
                    print(f"[epub-cleaner] {rel}: passed through", flush=True)
            except Exception as e:  # never wedge the queue on one bad file
                print(f"[epub-cleaner] {rel}: clean failed ({e}), passing through unchanged", flush=True)
                if os.path.exists(path):
                    _move(path, dst)
        last_sizes = seen
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--watch":
        watch(sys.argv[2], sys.argv[3])
    elif len(sys.argv) in (2, 3):
        print(f"{clean_epub(*sys.argv[1:])} change(s)")
    else:
        sys.exit(__doc__)
