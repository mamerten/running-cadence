"""Download the military cadence source videos listed in tools/cadence-sources.json.

Writes staging/cadence/<file> and staging/cadence/manifest.json, which
tools/import_cadence.py reads. Files already in staging/ are not re-downloaded.

Sources:
  dvids:<id>          a DVIDS video (US Gov work, public domain)
  commons:<File name> a Wikimedia Commons file (license read from Commons)
  local:<path>        a file already prepared in Mat's cadence library
                      (CADENCE_LIBRARY, default ~/Dropbox/Music/Military Cadences);
                      title/credit/license/source_url come from the entry itself

Rejected sources are skipped. Name sources to fetch only those (any part of
the file name or source, e.g. dvids:827771), including a rejected one you
want to re-check.

Usage:  python tools/fetch_cadence.py [source ...]
"""
import html
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = ROOT / "tools" / "cadence-sources.json"
# Source videos are big; set CADENCE_STAGING to keep them out of a synced folder.
STAGING = pathlib.Path(os.environ.get("CADENCE_STAGING") or ROOT / "staging" / "cadence")
UA = {"User-Agent": "running-cadence/1.0 (https://github.com/mamerten/running-cadence)"}
MAX_BYTES = 400 << 20     # skip giant full-resolution masters
LIBRARY = pathlib.Path(os.environ.get("CADENCE_LIBRARY")
                       or pathlib.Path.home() / "Dropbox" / "Music" / "Military Cadences")
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}


def get(url, headers=UA):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.geturl(), r.read()


def strip_tags(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def dvids(vid):
    url, page = get(f"https://www.dvidshub.net/video/{vid}", BROWSER_UA)
    page = page.decode("utf-8", "replace")
    title = html.unescape(re.search(r'og:title" content="([^"]*)"', page).group(1))
    mp4s = re.findall(r'https://d34w7g4gy10iej\.cloudfront\.net/video/[^"\']+\.mp4', page)
    # "Video by <a>Name</a>" then the unit: <h3 class="the_unit"><a>Unit</a>
    by = re.search(r"Video by\s*<a[^>]*>([^<]+)</a>", page)
    unit = re.search(r'class="the_unit"><a[^>]*>([^<]+)</a>', page)
    credit = ", ".join(html.unescape(m.group(1)).strip() for m in (by, unit) if m) or "U.S. military"
    return {"title": re.sub(r"[\"']", "", title).strip(), "credit": credit,
            "license": "Public domain (US Gov, DVIDS)", "source_url": url,
            "media": next((u for u in mp4s if "800k" in u), mp4s[0])}   # small stream when offered


def commons(name):
    q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo",
                                "titles": f"File:{name}", "iiprop": "url|extmetadata"})
    _, body = get(f"https://commons.wikimedia.org/w/api.php?{q}")
    info = next(iter(json.loads(body)["query"]["pages"].values()))["imageinfo"][0]
    meta = info["extmetadata"]
    title = re.sub(r"\s+\S{11}$", "", pathlib.Path(name).stem)   # drop the YouTube id suffix
    lic = meta.get("LicenseShortName", {}).get("value", "see source")
    artist = strip_tags(meta.get("Artist", {}).get("value", "")) or "U.S. Army"
    return {"title": title, "credit": artist, "license": f"{lic}, via Wikimedia Commons",
            "source_url": info["descriptionurl"], "media": info["url"]}


def main():
    STAGING.mkdir(parents=True, exist_ok=True)
    manifest = []
    wanted = sys.argv[1:]
    for s in json.loads(SOURCES.read_text(encoding="utf-8")):
        if wanted and not any(w in s["file"] or w in s["source"] for w in wanted):
            continue
        if s.get("reject") and not wanted:
            continue
        kind, ref = s["source"].split(":", 1)
        if kind == "local":                          # already-edited file: copy it in
            dest = STAGING / s["file"]
            if not dest.exists():
                dest.write_bytes((LIBRARY / ref).read_bytes())
            manifest.append({"file": s["file"], "kind": s.get("kind", "unknown"),
                             **{k: s[k] for k in ("title", "credit", "license", "source_url")}})
            print(f"{s['file'][:60]:60} {dest.stat().st_size // 1024:7d} KB  {s['title']}", flush=True)
            continue
        try:
            m = dvids(ref) if kind == "dvids" else commons(ref)
        except Exception as e:                       # page moved, removed, or blocked
            print(f"SKIP {s['file']}: {e}", flush=True)
            continue
        m["title"] = s.get("title") or m["title"]
        dest = STAGING / s["file"]
        if not dest.exists():
            req = urllib.request.Request(m["media"], headers=BROWSER_UA if kind == "dvids" else UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                if int(r.headers.get("Content-Length") or 0) > MAX_BYTES:
                    print(f"SKIP {s['file']}: over {MAX_BYTES >> 20} MB", flush=True)
                    continue
                dest.write_bytes(r.read())
        print(f"{s['file'][:60]:60} {dest.stat().st_size // 1024:7d} KB  {m['title']}", flush=True)
        manifest.append({"file": s["file"], "kind": s.get("kind", "unknown"),
                         **{k: m[k] for k in ("title", "credit", "license", "source_url")}})
    (STAGING / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
