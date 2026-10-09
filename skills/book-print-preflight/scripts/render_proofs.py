#!/usr/bin/env python3
"""Render a book PDF the way an artworker looks at it in Output Preview.

Usage:
  render_proofs.py FILE.pdf OUTDIR --kind cover|interior [--trim 5x8]
                   [--pages 1,5,12] [--tac-limit 240] [--dpi 150]

Writes PNGs for Claude to look at (with the Read tool):
  *_guides.png      page with trim (red), safe zone (blue dashed), spine folds
                    (green) and the KDP barcode box (orange) drawn on
  *_plate_C/M/Y/K   each CMYK separation as a black-on-white plate
  *_tac.png         ink heat map: grey = fine, yellow = over limit-20, red = over limit
  *_rgb_only.png    (cover) mask of where RGB objects sit, if any
  *_zoom_*.png      400% loupe tiles: spine, barcode area, title area, corners
Install deps: pip install pymupdf pillow
"""
import argparse, os, re, sys
import pymupdf
from PIL import Image, ImageDraw

PT = 72.0


def parse_trim(s):
    if not s:
        return None
    m = re.match(r"\s*([\d.]+)\s*[x×]\s*([\d.]+)", s)
    return (float(m.group(1)), float(m.group(2))) if m else None


def render_cmyk(page, dpi):
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csCMYK, alpha=False)
    return Image.frombytes("CMYK", (pix.width, pix.height), pix.samples)


def plates(cmyk, base):
    for i, name in enumerate("CMYK"):
        ch = cmyk.getchannel(i)
        # ink = dark, paper = white, like a film separation
        Image.eval(ch, lambda v: 255 - v).save(f"{base}_plate_{name}.png")


def tac_map(cmyk, base, limit):
    c, m, y, k = [list(cmyk.getchannel(i).tobytes()) for i in range(4)]
    out = Image.new("RGB", cmyk.size)
    lim = limit * 255 / 100
    warn = (limit - 20) * 255 / 100
    px = []
    worst = 0
    for a, b, cc, d in zip(c, m, y, k):
        t = a + b + cc + d
        worst = max(worst, t)
        if t > lim:
            px.append((230, 30, 30))
        elif t > warn:
            px.append((250, 200, 0))
        else:
            g = 255 - int(min(t, 765) / 765 * 160)
            px.append((g, g, g))
    out.putdata(px)
    out.save(f"{base}_tac.png")
    return round(worst * 100 / 255)


def draw_guides(rgb, page, trim, kind, dpi, page_index):
    s = dpi / PT
    im = rgb.copy()
    d = ImageDraw.Draw(im)
    W, H = page.rect.width, page.rect.height

    def rect(x0, y0, x1, y1, col, dash=False, w=2):
        x0, y0, x1, y1 = [v * s for v in (x0, y0, x1, y1)]
        if not dash:
            d.rectangle([x0, y0, x1, y1], outline=col, width=w)
            return
        step = 10
        for x in range(int(x0), int(x1), step * 2):
            d.line([x, y0, min(x + step, x1), y0], fill=col, width=w)
            d.line([x, y1, min(x + step, x1), y1], fill=col, width=w)
        for y in range(int(y0), int(y1), step * 2):
            d.line([x0, y, x0, min(y + step, y1)], fill=col, width=w)
            d.line([x1, y, x1, min(y + step, y1)], fill=col, width=w)

    def vline(x, col):
        d.line([x * s, 0, x * s, H * s], fill=col, width=2)

    regions = {}
    if kind == "cover" and trim:
        tw, th = trim
        b = (H / PT - th) / 2 * PT
        rect(b, b, W - b, H - b, "red")
        sl, sr = b + tw * PT, W - b - tw * PT
        vline(sl, "green"); vline(sr, "green")
        safe = 0.125 * PT
        rect(b + safe, b + safe, sl - safe, H - b - safe, "blue", dash=True)
        rect(sr + safe, b + safe, W - b - safe, H - b - safe, "blue", dash=True)
        if sr - sl > 0.125 * PT:
            rect(sl + 0.0625 * PT, b + safe, sr - 0.0625 * PT, H - b - safe, "blue", dash=True)
        # KDP barcode box: 2 x 1.2in, 0.25in in from the spine side and bottom of back cover
        bx1 = sl - 0.25 * PT
        by1 = H - b - 0.25 * PT
        rect(bx1 - 2 * PT, by1 - 1.2 * PT, bx1, by1, "orange")
        regions = {
            "spine": (sl - 0.3 * PT, b, sr + 0.3 * PT, H - b),
            "barcode": (bx1 - 2.3 * PT, by1 - 1.5 * PT, bx1 + 0.3 * PT, by1 + 0.4 * PT),
            "front_top": (sr, 0, W, H * 0.35),
            "front_bottom": (sr, H * 0.7, W, H),
            "back_text": (0, H * 0.15, sl, H * 0.6),
        }
    elif kind == "interior" and trim:
        tw, th = trim
        bleed = W / PT > tw + 0.06
        bx = 0.125 * PT if bleed else 0
        recto = page_index % 2 == 0
        tx0 = 0 if recto else bx
        tx1 = W - bx if recto else W
        ty0, ty1 = bx, H - bx
        rect(tx0, ty0, tx1, ty1, "red")
        n_pages = page.parent.page_count
        gut = 0.375 if n_pages <= 150 else 0.5 if n_pages <= 300 else 0.625 if n_pages <= 500 else 0.75 if n_pages <= 700 else 0.875
        out = 0.375 if bleed else 0.25
        gx0 = tx0 + (gut if recto else out) * PT
        gx1 = tx1 - (out if recto else gut) * PT
        rect(gx0, ty0 + 0.25 * PT, gx1, ty1 - 0.25 * PT, "blue", dash=True)
        regions = {"top": (0, 0, W, H * 0.2), "gutter": ((0, 0, W * 0.3, H) if recto else (W * 0.7, 0, W, H))}
    return im, regions


def zooms(page, regions, base, zoom_dpi=300):
    for name, (x0, y0, x1, y1) in regions.items():
        clip = pymupdf.Rect(x0, y0, x1, y1) & page.rect
        if clip.is_empty:
            continue
        # keep tiles a sensible size for viewing
        area_in2 = clip.width * clip.height / PT / PT
        dpi = zoom_dpi if area_in2 < 6 else 200 if area_in2 < 20 else 120
        page.get_pixmap(dpi=dpi, clip=clip).save(f"{base}_zoom_{name}.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("outdir")
    ap.add_argument("--kind", choices=["cover", "interior"], required=True)
    ap.add_argument("--trim")
    ap.add_argument("--pages", help="comma list of 1-based pages (interiors: pick a sample)")
    ap.add_argument("--tac-limit", type=int, default=240)
    ap.add_argument("--dpi", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    doc = pymupdf.open(a.pdf)
    trim = parse_trim(a.trim)
    if a.pages:
        idx = [int(p) - 1 for p in a.pages.split(",")]
    elif a.kind == "cover":
        idx = [0]
    else:
        n = len(doc)
        idx = sorted(set([0, 1, 2, 3, 4, 5, n // 4, n // 2, n // 2 + 1, 3 * n // 4, n - 2, n - 1]) & set(range(n)))
    stem = os.path.splitext(os.path.basename(a.pdf))[0]
    for i in idx:
        page = doc[i]
        dpi = a.dpi or (100 if a.kind == "cover" else 110)
        base = os.path.join(a.outdir, f"{stem}_p{i+1}")
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        rgb = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        guided, regions = draw_guides(rgb, page, trim, a.kind, dpi, i)
        guided.save(f"{base}_guides.png")
        cmyk = render_cmyk(page, dpi)
        if a.kind == "cover":
            plates(cmyk, base)
        worst = tac_map(cmyk, base, a.tac_limit)
        zooms(page, regions, base)
        print(f"page {i+1}: max TAC {worst}% -> {base}_*.png")
    print("Done. Look at *_guides.png first, then *_tac.png, plates, and zooms.")


if __name__ == "__main__":
    main()
