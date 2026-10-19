"""Download the military cadence source videos listed in tools/cadence-sources.json.

Writes staging/cadence/<file> and staging/cadence/manifest.json, which
tools/import_cadence.py reads. Files already in staging/ are not re-downloaded.

Sources:
  dvids:<id>          a DVIDS video (US Gov work, public domain)
  commons:<File name> a Wikimedia Commons file (license read from Commons)

Usage:  python tools/fetch_cadence.py
"""
import html
import json
import pathlib
import re
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = ROOT / "tools" / "cadence-sources.json"
STAGING = ROOT / "staging" / "cadence"
UA = {"User-Agent": "running-cadence/1.0 (https://github.com/mamerten/running-cadence)"}
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
            "license": "Public domain (US Gov, DVIDS)", "source_url": url, "media": mp4s[0]}


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
    for s in json.loads(SOURCES.read_text(encoding="utf-8")):
        kind, ref = s["source"].split(":", 1)
        try:
            m = dvids(ref) if kind == "dvids" else commons(ref)
        except Exception as e:                       # page moved, removed, or blocked
            print(f"SKIP {s['file']}: {e}", flush=True)
            continue
        m["title"] = s.get("title") or m["title"]
        dest = STAGING / s["file"]
        if not dest.exists():
            _, data = get(m["media"], BROWSER_UA if kind == "dvids" else UA)
            dest.write_bytes(data)
        print(f"{s['file'][:60]:60} {dest.stat().st_size // 1024:7d} KB  {m['title']}", flush=True)
        manifest.append({"file": s["file"], "kind": s.get("kind", "unknown"),
                         **{k: m[k] for k in ("title", "credit", "license", "source_url")}})
    (STAGING / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
