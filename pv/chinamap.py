"""China, drawn from a national-standard boundary set.

Source: 阿里云 DataV 地理小工具系列 areas_v3 全国边界，审图号 **GS(2019)1719号**。It is a Chinese
domestic dataset carrying a 审图号, it carries all 34 province-level units **including 台湾省、香港、澳门**,
and it carries the 南海诸岛 boundary as the separate feature `100000_JD`. Per the map-compliance rule
no overseas tile source (Google / Apple / Bing overseas / OSM / Mapbox) is used anywhere in this film.

Projection: Albers equal-area conic, standard parallels 25N and 47N, central meridian 105E, latitude
of origin 35N -- the conventional projection for a map of all of China. x and y share one scale
factor, so the country is not stretched to fill the frame.

Layout follows the national standard for a full map: the mainland with 海南 and 台湾 in the main frame,
and the South China Sea -- 南海诸岛 and the 九段线 -- in an inset in the corner.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
GEOJSON = ROOT / "work" / "map" / "china_full.json"

JD_ADCODE = "100000_JD"

# the extent a full map of China has to cover
MAIN_BOX = (73.0, 17.0, 136.0, 54.0)      # 海南 18N and 台湾 22N both fall inside
INSET_BOX = (105.0, 3.0, 125.0, 23.0)     # 南海诸岛 + 九段线

APPROVAL = "GS(2019)1719号"               # 审图号, printed on the frame the way a published map prints it

P1, P2 = math.radians(25.0), math.radians(47.0)
LON0 = math.radians(105.0)
LAT0 = math.radians(35.0)
_N = 0.5 * (math.sin(P1) + math.sin(P2))
_C = math.cos(P1) ** 2 + 2 * _N * math.sin(P1)
_RHO0 = math.sqrt(_C - 2 * _N * math.sin(LAT0)) / _N


def project(lon: float, lat: float) -> tuple[float, float]:
    """Albers. y grows southward from the latitude of origin, i.e. it is already screen-oriented
    (north is up), which is what a raster wants."""
    lon, lat = math.radians(lon), math.radians(lat)
    rho = math.sqrt(_C - 2 * _N * math.sin(lat)) / _N
    th = _N * (lon - LON0)
    return rho * math.sin(th), rho * math.cos(th) - _RHO0


@lru_cache(1)
def _rings() -> tuple[tuple, tuple]:
    """Every ring, already projected, split into (mainland+islands, south-sea)."""
    d = json.loads(GEOJSON.read_text(encoding="utf-8"))
    land, jd = [], []
    for f in d["features"]:
        name = str(f.get("properties", {}).get("adcode", ""))
        geom = f.get("geometry") or {}
        polys = geom.get("coordinates") or []
        if geom.get("type") == "Polygon":
            polys = [polys]
        for poly in polys:
            for ring in poly:
                pts = [project(float(x), float(y)) for x, y in ring]
                if len(pts) >= 3:
                    (jd if name == JD_ADCODE else land).extend([pts])
    return tuple(land), tuple(jd)


@lru_cache(8)
def _fit(which: str, w: int, h: int) -> tuple[float, float, float]:
    """The one scale factor and offset that place a frame inside a (w, h) image, centred.

    The frame is fitted to the **lat/lon box**, not to the data's own extent. 海南省 is a
    MultiPolygon that reaches 曾母暗沙 at 4N, so fitting to the data would push the mainland into a
    corner; the box is what decides the frame, and anything outside it is simply clipped."""
    box = INSET_BOX if which == "inset" else MAIN_BOX
    lon0, lat0, lon1, lat1 = box
    pts = [project(lon0 + (lon1 - lon0) * i / 32, lat0 + (lat1 - lat0) * j / 32)
           for i in range(33) for j in range(33)]
    px0 = min(x for x, _ in pts)
    px1 = max(x for x, _ in pts)
    py0 = min(y for _, y in pts)
    py1 = max(y for _, y in pts)
    k = min(w / max(1e-9, px1 - px0), h / max(1e-9, py1 - py0)) * 0.94
    ox = (w - (px1 - px0) * k) / 2 - px0 * k
    oy = (h - (py1 - py0) * k) / 2 - py0 * k
    return k, ox, oy


def to_px(lon: float, lat: float, w: int, h: int, which: str = "main") -> tuple[float, float]:
    k, ox, oy = _fit(which, w, h)
    x, y = project(lon, lat)
    return x * k + ox, y * k + oy


def _box_mask(w: int, h: int, box, which: str) -> Image.Image:
    """The frame itself, as a filled shape, so nothing outside it bleeds in. Without this a few
    South China Sea reefs belonging to 海南省 poke out along the bottom edge of the main frame,
    half-drawn -- which is exactly the kind of partial territory a published map must not show."""
    lon0, lat0, lon1, lat1 = box
    k, ox, oy = _fit(which, w, h)
    ring = []
    n = 24
    for i in range(n + 1):                      # bottom edge, west to east
        ring.append((lon0 + (lon1 - lon0) * i / n, lat0))
    for j in range(n + 1):                      # east edge, south to north
        ring.append((lon1, lat0 + (lat1 - lat0) * j / n))
    for i in range(n + 1):                      # top edge, east to west
        ring.append((lon1 - (lon1 - lon0) * i / n, lat1))
    for j in range(n + 1):                      # west edge, north to south
        ring.append((lon0, lat1 - (lat1 - lat0) * j / n))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon([(x * k + ox, y * k + oy) for x, y in
                               (project(lo, la) for lo, la in ring)], fill=255)
    return m


@lru_cache(64)
def land_mask(w: int, h: int) -> Image.Image:
    """Land-only mask (mainland + 海南 + 台湾 + 港澳), at exactly (w, h), clipped to the main frame."""
    land, _ = _rings()
    k, ox, oy = _fit("main", w, h)
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for r in land:
        d.polygon([(x * k + ox, y * k + oy) for x, y in r], fill=255)
    return ImageChops.multiply(im, _box_mask(w, h, MAIN_BOX, "main"))


@lru_cache(64)
def sea_mask(w: int, h: int) -> Image.Image:
    """南海诸岛 + 九段线, drawn inside its own inset frame and clipped to it."""
    _, jd = _rings()
    k, ox, oy = _fit("inset", w, h)
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for r in jd:
        d.polygon([(x * k + ox, y * k + oy) for x, y in r], fill=255)
    return ImageChops.multiply(im, _box_mask(w, h, INSET_BOX, "inset"))


@lru_cache(64)
def land_cells(w: int, h: int, cell: int = 3) -> Image.Image:
    """The map quantised to a terminal grid: one cell per land block. This is what the film draws."""
    cols, rows = max(4, w // cell), max(4, h // cell)
    return land_mask(cols, rows)


@lru_cache(64)
def sea_cells(w: int, h: int, cell: int = 2) -> Image.Image:
    cols, rows = max(4, w // cell), max(4, h // cell)
    return sea_mask(cols, rows)


def graticule(w: int, h: int, step: int = 10) -> tuple[list, list]:
    """Meridians and parallels for the main frame. Returns ([lon_lines], [lat_lines]), each a list of
    pixel points. Lat/lon rulers are what make a silhouette read as a map."""
    lon0, lat0, lon1, lat1 = MAIN_BOX
    lats = [lat0 + (lat1 - lat0) * i / 48 for i in range(49)]
    lons = [lon0 + (lon1 - lon0) * i / 48 for i in range(49)]
    meridians = [[to_px(lon, lat, w, h) for lat in lats]
                 for lon in range(int(lon0 // step * step) + step, int(lon1) + 1, step)]
    parallels = [[to_px(lon, lat, w, h) for lon in lons]
                 for lat in range(int(lat0 // step * step) + step, int(lat1) + 1, step)]
    return meridians, parallels
