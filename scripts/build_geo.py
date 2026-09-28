"""Build the region boundaries the studio's maps draw.

    python scripts/build_geo.py

Source: UN OCHA Common Operational Dataset, administrative boundaries of Ethiopia
(COD-AB, 2025), level 1, from the Humanitarian Data Exchange (dataset `cod-ab-eth`,
licence CC BY-IGO). It is the only public boundary set found that has all 14 regions
the 2024-25 EDHS reports, including Sidama, South West Ethiopia, Central Ethiopia and
South Ethiopia. geoBoundaries' Ethiopia file is from 2016 and predates all four.

Steps:
  1. download the GeoJSON bundle once, into outputs/geo/raw/ (not committed);
  2. keep the admin-1 layer and two properties, the P-code and the name;
  3. simplify with mapshaper (npx; no Python geo stack is needed) to a size a phone
     can load, keeping shared borders shared so neighbouring regions still meet;
  4. check that every survey region joins to exactly one polygon.

Output: app/public/geo/regions.geojson.
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "outputs" / "geo" / "raw"
OUT = ROOT / "app" / "public" / "geo" / "regions.geojson"

HDX_PACKAGE = "https://data.humdata.org/api/3/action/package_show?id=cod-ab-eth"

# Survey region -> OCHA P-code. Mirrors app/src/lib/regions.ts.
REGIONS = {
    "Tigray": "ET01", "Afar": "ET02", "Amhara": "ET03", "Oromia": "ET04",
    "Somali": "ET05", "Benishangul-Gumuz": "ET06", "Central Ethiopia": "ET07",
    "South Ethiopia": "ET08", "South West Ethiopia": "ET11", "Gambella": "ET12",
    "Harari": "ET13", "Addis Ababa": "ET14", "Dire Dawa": "ET15", "Sidama": "ET16",
}
CONTESTED = "ET99"

# Percentage of vertices mapshaper keeps. 10% keeps borders smooth at national
# and regional zoom (Harari, the smallest, keeps its shape) for about 50 KB.
KEEP = "10%"


def download() -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / "eth_admin1.geojson"
    if target.exists():
        return target
    meta = json.load(urllib.request.urlopen(HDX_PACKAGE, timeout=60))["result"]
    res = next(r for r in meta["resources"] if r["format"] == "GeoJSON")
    print(f"downloading {res['url']}")
    data = urllib.request.urlopen(res["url"], timeout=300).read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        target.write_bytes(z.read("eth_admin1.geojson"))
    (RAW / "SOURCE.txt").write_text(
        f"{meta['title']}\n{res['url']}\nlicence: {meta.get('license_title')}\n", encoding="utf-8")
    return target


def main():
    src = download()
    g = json.loads(src.read_text(encoding="utf-8"))

    # Keep only what the app joins on, so the file carries no unused attributes.
    feats = []
    for f in g["features"]:
        p = f["properties"]
        feats.append({"type": "Feature", "geometry": f["geometry"],
                      "properties": {"pcode": p["adm1_pcode"], "ocha_name": p["adm1_name"]}})
    slim = RAW / "admin1_slim.geojson"
    slim.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        sys.exit("npx not found: install Node.js to simplify the boundaries")
    cmd = [npx, "--yes", "mapshaper@0.6", str(slim),
           "-simplify", KEEP, "keep-shapes",
           "-clean",
           "-o", "precision=0.0001", "format=geojson", str(OUT)]
    subprocess.run(cmd, check=True)

    out = json.loads(OUT.read_text(encoding="utf-8"))
    codes = [f["properties"]["pcode"] for f in out["features"]]
    missing = [r for r, c in REGIONS.items() if codes.count(c) != 1]
    if missing:
        sys.exit(f"regions without exactly one polygon: {missing}")
    extra = sorted(set(codes) - set(REGIONS.values()) - {CONTESTED})
    if extra:
        sys.exit(f"unexpected polygons: {extra}")
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.relative_to(ROOT)}: {len(codes)} polygons, {kb:.0f} KB; "
          f"all 14 survey regions join")


if __name__ == "__main__":
    main()
