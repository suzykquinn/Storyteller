#!/usr/bin/env python3
"""Measure everything a pre-press artworker would measure in a book PDF.

Usage:
  preflight.py FILE.pdf --kind cover|interior [--trim 5x8] [--pages N]
               [--paper white|cream|colour|premium-colour] [--printer kdp|ingram]
               [--json out.json]

Prints a human-readable fact sheet (and optionally JSON). It does NOT decide
pass/fail on its own: Claude compares these facts against references/*.md.
Install deps: pip install pymupdf pikepdf pillow
"""
import argparse, json, re, sys, math
from collections import Counter, defaultdict

import pymupdf
import pikepdf

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content_scan import scan_page, classify

PT = 72.0  # points per inch


def inch(v):
    return round(v / PT, 4)


def parse_trim(s):
    if not s:
        return None
    m = re.match(r"\s*([\d.]+)\s*[x×]\s*([\d.]+)", s)
    if not m:
        sys.exit(f"Can't read trim size '{s}', use e.g. 5x8 or 5.5x8.5 (inches)")
    return float(m.group(1)), float(m.group(2))


# ---------------------------------------------------------------- document level
def doc_facts(path, pdf):
    f = {}
    f["pdf_version"] = str(pdf.pdf_version)
    root = pdf.Root
    f["encrypted"] = pdf.is_encrypted
    oi = []
    for intent in root.get("/OutputIntents", []) or []:
        oi.append({
            "subtype": str(intent.get("/S", "")),
            "condition": str(intent.get("/OutputConditionIdentifier", "")),
            "info": str(intent.get("/Info", "")),
            "has_icc": "/DestOutputProfile" in intent,
        })
    f["output_intents"] = oi
    info = pdf.docinfo
    f["gts_pdfx_version"] = str(info.get("/GTS_PDFXVersion", "")) or None
    f["creator"] = str(info.get("/Creator", "")) or None
    f["producer"] = str(info.get("/Producer", "")) or None
    f["has_layers_ocg"] = "/OCProperties" in root
    f["has_acroform"] = "/AcroForm" in root and len(root.AcroForm.get("/Fields", [])) > 0
    f["has_javascript"] = "/Names" in root and "/JavaScript" in root.Names
    return f


# ---------------------------------------------------------------- resources walk
def walk_resources(pdf):
    """Collect colour spaces, spot names, overprint/transparency use, fonts, images."""
    spots = Counter()
    devicen = Counter()
    cs_kinds = Counter()
    icc_profiles = set()
    overprint_gs = 0
    transparency = Counter()
    image_cs = Counter()

    def cs_name(cs):
        if isinstance(cs, pikepdf.Name):
            return str(cs)
        if isinstance(cs, pikepdf.Array) and len(cs):
            return str(cs[0])
        return "?"

    def note_cs(cs):
        try:
            name = cs_name(cs)
            cs_kinds[name] += 1
            if name == "/Separation":
                spots[str(cs[1])] += 1
            elif name == "/DeviceN":
                devicen[" + ".join(str(n) for n in cs[1])] += 1
            elif name == "/ICCBased":
                n = int(cs[1].get("/N", 0))
                icc_profiles.add({1: "Gray", 3: "RGB", 4: "CMYK"}.get(n, f"N={n}"))
            elif name == "/Indexed":
                note_cs(cs[1])
        except Exception:
            pass

    for obj in pdf.objects:
        if not isinstance(obj, (pikepdf.Dictionary, pikepdf.Stream)):
            continue
        t = obj.get("/Type")
        st = obj.get("/Subtype")
        if t == "/ExtGState" or ("/OP" in obj or "/op" in obj or "/OPM" in obj):
            if obj.get("/OP") is True or obj.get("/op") is True:
                overprint_gs += 1
            if "/SMask" in obj and obj.SMask != pikepdf.Name("/None"):
                transparency["soft masks"] += 1
            ca = obj.get("/ca", 1)
            CA = obj.get("/CA", 1)
            try:
                if float(ca) < 1 or float(CA) < 1:
                    transparency["opacity < 100%"] += 1
            except Exception:
                pass
            bm = obj.get("/BM")
            if bm is not None and str(bm) not in ("/Normal", "/Compatible"):
                transparency[f"blend mode {bm}"] += 1
        if st == "/Image":
            cs = obj.get("/ColorSpace")
            if cs is not None:
                note_cs(cs)
                image_cs[cs_name(cs)] += 1
            elif obj.get("/ImageMask"):
                image_cs["stencil mask"] += 1
            if "/SMask" in obj:
                transparency["images with alpha"] += 1
        if st == "/Form" and "/Group" in obj and obj.Group.get("/S") == "/Transparency":
            transparency["transparency groups"] += 1
        if "/ColorSpace" in obj and isinstance(obj.ColorSpace, pikepdf.Dictionary):
            for _, cs in obj.ColorSpace.items():
                note_cs(cs)
    return {
        "spot_colours": dict(spots),
        "devicen": dict(devicen),
        "colour_space_kinds": dict(cs_kinds),
        "icc_profile_types": sorted(icc_profiles),
        "overprint_graphics_states": overprint_gs,
        "transparency": dict(transparency),
        "image_colour_spaces": dict(image_cs),
    }


def spot_problems(spots):
    probs = []
    names = list(spots)
    norm = defaultdict(list)
    for n in names:
        key = re.sub(r"[^a-z0-9]", "", n.lower().replace("pantone", "pms"))
        norm[key].append(n)
    for k, v in norm.items():
        if len(v) > 1:
            probs.append(f"Near-duplicate spot names (would make extra plates): {v}")
    for n in names:
        if n.strip("/").lower() in ("all",):
            probs.append("Registration colour ('All') used as a spot: prints on every plate")
        if re.search(r"(cyan|magenta|yellow|black)$", n.lower()):
            probs.append(f"Spot named like a process ink: {n}")
    return probs


# ---------------------------------------------------------------- fonts
def font_facts(path):
    doc = pymupdf.open(path)
    fonts = {}
    for pno in range(len(doc)):
        for xref, ext, ftype, basefont, name, enc, *_ in doc.get_page_fonts(pno, full=True):
            key = basefont or name
            if key in fonts:
                fonts[key]["pages"].add(pno + 1)
                continue
            embedded = ext not in ("n/a", "")
            fonts[key] = {
                "type": ftype,
                "embedded": embedded,
                "subset": bool(re.match(r"^[A-Z]{6}\+", basefont or "")),
                "pages": {pno + 1},
            }
    out = []
    for k, v in fonts.items():
        pages = sorted(v["pages"])
        out.append({**v, "name": k, "pages": pages[:10] + (["..."] if len(pages) > 10 else [])})
    return out


# ---------------------------------------------------------------- images
def image_facts(doc):
    rows = []
    for page in doc:
        seen = set()
        for info in page.get_image_info(xrefs=True):
            xref = info.get("xref", 0)
            bbox = pymupdf.Rect(info["bbox"])
            if bbox.is_empty or bbox.width < 2 or bbox.height < 2:
                continue
            w_in, h_in = bbox.width / PT, bbox.height / PT
            ppi_x = info["width"] / w_in
            ppi_y = info["height"] / h_in
            key = (xref, tuple(round(c) for c in bbox))
            if key in seen:
                continue
            seen.add(key)
            visible = bbox & page.rect
            rows.append({
                "page": page.number + 1,
                "xref": xref,
                "pixels": f"{info['width']}x{info['height']}",
                "placed_in": f"{w_in:.2f}x{h_in:.2f}",
                "effective_ppi": round(min(ppi_x, ppi_y)),
                "colorspace_components": info.get("colorspace"),
                "bpc": info.get("bpc"),
                "bbox_in": [inch(bbox.x0), inch(bbox.y0), inch(bbox.x1), inch(bbox.y1)],
                "pct_of_page": round(100 * visible.get_area() / page.rect.get_area(), 1) if not visible.is_empty else 0,
                "upscale_suspect": None,
            })
    # Upscale heuristic on the big images only (costly): an image that was blown
    # up from a smaller original has little detail above its true resolution, so
    # shrinking it to half size and back loses almost nothing.
    try:
        from PIL import Image, ImageChops, ImageStat
        import io
        checked = {}
        for r in rows:
            if r["pct_of_page"] < 5 or r["xref"] in checked or not r["xref"]:
                r["upscale_suspect"] = checked.get(r["xref"])
                continue
            try:
                pix = pymupdf.Pixmap(doc, r["xref"])
                if pix.n - pix.alpha >= 4:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
                if max(im.size) > 2400:
                    im.thumbnail((2400, 2400))
                def roundtrip(f):
                    sm = im.resize((max(1, im.width // f), max(1, im.height // f)), Image.LANCZOS)
                    return ImageStat.Stat(ImageChops.difference(im, sm.resize(im.size, Image.LANCZOS))).mean[0]
                d2, d4 = roundtrip(2), roundtrip(4)
                # Real detail spreads across scales; an upscaled image has almost
                # nothing in its finest octave compared with the next one down.
                ratio = d2 / max(d4, 1e-6)
                diff = round(ratio, 3)
                verdict = ratio < 0.33 and d4 > 0.3  # ignore flat graphics
                checked[r["xref"]] = verdict
                r["upscale_suspect"] = verdict
                r["detail_score"] = round(diff, 2)
            except Exception:
                pass
    except ImportError:
        pass
    return rows


# ---------------------------------------------------------------- text
def text_facts(page):
    """Size/colour of every text run, via the text trace (gives real colour spaces)."""
    runs = []
    for t in page.get_texttrace():
        size = t["size"] * abs(t.get("scale", 1) or 1)
        color = tuple(round(c, 3) for c in (t.get("color") or ()))
        ncomp = t.get("colorspace", len(color))
        text = "".join(chr(c[0]) for c in t["chars"] if c[0] > 0)
        if not text.strip():
            continue
        x0, y0, x1, y1 = t["bbox"]
        runs.append({
            "text": text[:60], "size": round(size, 2), "font": t.get("font"),
            "ncomp": ncomp, "color": color, "bbox": (x0, y0, x1, y1),
            "type": t.get("type"), "opacity": t.get("opacity", 1),
        })
    return runs


# ---------------------------------------------------------------- vector lines
# ---------------------------------------------------------------- ink coverage
def ink_coverage(page, dpi=50):
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csCMYK, alpha=False)
    s = pix.samples
    n = pix.width * pix.height
    tac_max = 0
    over240 = over300 = 0
    totals = [0, 0, 0, 0]
    for i in range(0, len(s), 4):
        c, m, y, k = s[i], s[i + 1], s[i + 2], s[i + 3]
        totals[0] += c; totals[1] += m; totals[2] += y; totals[3] += k
        t = c + m + y + k
        if t > tac_max:
            tac_max = t
        if t > 612:  # 240% of 255
            over240 += 1
            if t > 765:
                over300 += 1
    pct = lambda v: round(v * 100 / 255, 1)
    return {
        "max_tac_pct": pct(tac_max),
        "pct_area_over_240": round(100 * over240 / n, 2),
        "pct_area_over_300": round(100 * over300 / n, 2),
        "avg_cmyk_pct": [pct(t / n) for t in totals],
        "has_colour_ink": any(t / n > 0.5 for t in totals[:3]),
    }


def has_visible_colour(page, dpi=30, chroma=30, min_px=6):
    """True if the page shows real colour (not just black/grey made of CMY)."""
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    s = pix.samples
    hits = 0
    for i in range(0, len(s), 3):
        r, g, b = s[i], s[i + 1], s[i + 2]
        if max(r, g, b) - min(r, g, b) > chroma:
            hits += 1
            if hits >= min_px:
                return True
    return False


def bleed_gaps(page, edges=("top", "bottom", "left", "right"), dpi=144):
    """Find white slivers where artwork stops short of the bleed edge.

    Compares the outermost strip of the page with a strip just inside the trim:
    if the inside is mostly ink but the very edge is paper-white, the art
    doesn't reach the bleed and a white line can show after trimming.
    """
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    w, h, s = pix.width, pix.height, pix.samples
    edge_px = max(1, int(0.02 * dpi))          # outermost ~0.02in
    inner_at = int(0.16 * dpi)                  # just inside the trim

    def white(x, y):
        i = (y * w + x) * 3
        return s[i] > 245 and s[i + 1] > 245 and s[i + 2] > 245

    def frac(points):
        pts = list(points)
        return sum(white(x, y) for x, y in pts) / max(1, len(pts))

    out = {}
    lines = {
        "top": (lambda k: ((x, k) for x in range(0, w, 3)), 0, inner_at),
        "bottom": (lambda k: ((x, h - 1 - k) for x in range(0, w, 3)), 0, inner_at),
        "left": (lambda k: ((k, y) for y in range(0, h, 3)), 0, inner_at),
        "right": (lambda k: ((w - 1 - k, y) for y in range(0, h, 3)), 0, inner_at),
    }
    for e in edges:
        gen, _, inner = lines[e]
        outer_white = max(frac(gen(k)) for k in range(edge_px))
        inner_white = frac(gen(inner))
        if outer_white - inner_white > 0.25:
            # measure how deep the gap goes
            depth = 0
            while depth < inner and frac(gen(depth)) - inner_white > 0.25:
                depth += 1
            out[e] = {"white_pct_at_edge": round(outer_white * 100), "white_pct_inside": round(inner_white * 100),
                      "gap_in": round(depth / dpi, 3)}
    return out


# ---------------------------------------------------------------- cover geometry
SPINE_PER_PAGE = {
    "kdp": {"white": 0.002252, "cream": 0.0025, "colour": 0.002252, "premium-colour": 0.002347},
    # IngramSpark varies by paper/binding; these are typical and must be checked
    # against Ingram's cover template generator.
    "ingram": {"white": 0.002252, "cream": 0.0025, "colour": 0.002252, "premium-colour": 0.002347},
}


def cover_geometry(page, trim, pages, paper, printer):
    W, H = page.rect.width / PT, page.rect.height / PT
    g = {"page_in": [round(W, 4), round(H, 4)]}
    tb = page.trimbox if page.trimbox != page.mediabox else None
    if tb:
        g["trimbox_in"] = [inch(tb.width), inch(tb.height)]
    if trim:
        tw, th = trim
        bleed_h = (H - th) / 2
        g["bleed_top_bottom_in"] = round(bleed_h, 4)
        spine = W - 2 * tw - 2 * bleed_h
        g["implied_spine_in"] = round(spine, 4)
        if pages and paper:
            per = SPINE_PER_PAGE.get(printer or "kdp", SPINE_PER_PAGE["kdp"]).get(paper)
            if per:
                exp = pages * per
                g["expected_spine_in"] = round(exp, 4)
                g["expected_cover_in"] = [round(2 * tw + exp + 0.25, 4), round(th + 0.25, 4)]
                g["spine_diff_in"] = round(spine - exp, 4)
        g["zones_in_from_left"] = {
            "back_cover": [round(bleed_h, 3), round(bleed_h + tw, 3)],
            "spine": [round(bleed_h + tw, 3), round(W - bleed_h - tw, 3)],
            "front_cover": [round(W - bleed_h - tw, 3), round(W - bleed_h, 3)],
        }
    return g


def text_near_edges(page, runs, trim, kind, page_index, safe=0.125, spine_safe=0.0625):
    """Text runs that sit outside the safe area. Returns list of (text, why)."""
    W, H = page.rect.width, page.rect.height
    hits = []
    if kind == "cover" and trim:
        tw, th = trim
        b = (H / PT - th) / 2
        left_trim, right_trim = b * PT, W - b * PT
        top_trim, bot_trim = b * PT, H - b * PT
        spine_l = (b + tw) * PT
        spine_r = W - (b + tw) * PT
        for r in runs:
            x0, y0, x1, y1 = r["bbox"]
            why = []
            if x0 < left_trim + safe * PT or x1 > right_trim - safe * PT:
                why.append("within 0.125in of the left/right trim")
            if y0 < top_trim + safe * PT or y1 > bot_trim - safe * PT:
                why.append("within 0.125in of top/bottom trim")
            crosses_spine = (x0 < spine_l < x1) or (x0 < spine_r < x1)
            on_spine = x0 >= spine_l - 1 and x1 <= spine_r + 1
            if crosses_spine:
                why.append("crosses a spine fold")
            elif not on_spine and (abs(x1 - spine_l) < safe * PT or abs(x0 - spine_r) < safe * PT
                                   or (x1 <= spine_l and x1 > spine_l - safe * PT)
                                   or (x0 >= spine_r and x0 < spine_r + safe * PT)):
                why.append("within 0.125in of a spine fold (will wrap round the spine)")
            elif on_spine and spine_r - spine_l > 2 * spine_safe * PT and (
                x0 < spine_l + spine_safe * PT or x1 > spine_r - spine_safe * PT):
                why.append("closer than 0.0625in to a spine fold")
            if why:
                hits.append((r["text"], r["size"], "; ".join(why)))
    return hits


def interior_margins(doc, page_count, bleed):
    """Min distance from text to each edge, split by recto/verso, measured from trim."""
    if page_count <= 150: gutter_need = 0.375
    elif page_count <= 300: gutter_need = 0.5
    elif page_count <= 500: gutter_need = 0.625
    elif page_count <= 700: gutter_need = 0.75
    else: gutter_need = 0.875
    outside_need = 0.375 if bleed else 0.25
    worst = {"gutter": 99, "outside": 99, "top": 99, "bottom": 99}
    offenders = []
    for page in doc:
        W, H = page.rect.width, page.rect.height
        bx = 0.125 * PT if bleed else 0
        by = 0.125 * PT if bleed else 0
        recto = (page.number % 2 == 0)  # page 1 is a right-hand page
        blocks = [b for b in page.get_text("blocks") if b[4].strip()]
        for x0, y0, x1, y1, txt, *_ in blocks:
            # with bleed, the extra width is on the outside edge only
            if recto:
                gutter = x0 / PT
                outside = (W - bx - x1) / PT
            else:  # verso: gutter is the right edge, bleed sits on the left
                gutter = (W - x1) / PT
                outside = (x0 - bx) / PT
            top = (y0 - by) / PT
            bottom = (H - by - y1) / PT
            for k, v in (("gutter", gutter), ("outside", outside), ("top", top), ("bottom", bottom)):
                worst[k] = min(worst[k], v)
            if gutter < gutter_need - 0.01 or outside < outside_need - 0.01 or top < 0.25 - 0.01 or bottom < 0.25 - 0.01:
                if len(offenders) < 25:
                    offenders.append({"page": page.number + 1, "text": txt.strip()[:50],
                                      "gutter": round(gutter, 3), "outside": round(outside, 3),
                                      "top": round(top, 3), "bottom": round(bottom, 3)})
    return {"gutter_required_in": gutter_need, "outside_required_in": outside_need,
            "worst_in": {k: round(v, 3) for k, v in worst.items()}, "offenders": offenders}


def isbn13_ok(digits):
    if len(digits) != 13:
        return False
    tot = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    return (10 - tot % 10) % 10 == int(digits[12])


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--kind", choices=["cover", "interior"], required=True)
    ap.add_argument("--trim", help="trim size in inches, e.g. 5x8")
    ap.add_argument("--pages", type=int, help="interior page count (for spine/gutter)")
    ap.add_argument("--paper", choices=["white", "cream", "colour", "premium-colour"])
    ap.add_argument("--printer", choices=["kdp", "ingram"])
    ap.add_argument("--json")
    ap.add_argument("--max-pages", type=int, default=2000, help="cap pages analysed in detail")
    a = ap.parse_args()

    trim = parse_trim(a.trim)
    doc = pymupdf.open(a.pdf)
    pdf = pikepdf.open(a.pdf)
    R = {"file": a.pdf, "kind": a.kind, "page_count": len(doc)}
    R["document"] = doc_facts(a.pdf, pdf)
    R["resources"] = walk_resources(pdf)
    R["spot_problems"] = spot_problems(R["resources"]["spot_colours"])
    R["fonts"] = font_facts(a.pdf)

    sizes = Counter((round(p.rect.width / PT, 3), round(p.rect.height / PT, 3)) for p in doc)
    R["page_sizes_in"] = [{"size": f"{w}x{h}", "count": c} for (w, h), c in sizes.items()]
    if trim and a.kind == "interior":
        (w, h), _ = sizes.most_common(1)[0]
        tw, th = trim
        if abs(w - tw) < 0.01 and abs(h - th) < 0.01:
            R["interior_bleed"] = False
        elif abs(w - (tw + 0.125)) < 0.01 and abs(h - (th + 0.25)) < 0.01:
            R["interior_bleed"] = True
        else:
            R["interior_bleed"] = None
            R["interior_size_problem"] = f"Page {w}x{h}in matches neither {tw}x{th} (no bleed) nor {tw+0.125}x{th+0.25} (bleed)"

    R["images"] = image_facts(doc)

    text_summary = Counter()
    text_flags = {}
    min_size = None
    hair = []
    ink = []
    edge_hits = []
    blank_pages = []
    colour_pages = []
    colour_use = Counter()
    overprint_whites = []
    for page in list(doc)[: a.max_pages]:
        runs = text_facts(page)  # readable text + positions (colours here are RGB-converted)
        events = scan_page(pdf.pages[page.number], page.rect.height)  # true colours
        thin = []
        for e in events:
            fam, det, val = e["fill"]
            colour_use[f"{e['kind']}: {fam}" + (f" {det}" if det else "")] += 1
            if e["kind"] == "text":
                cls = classify(e["fill"], e["size"], e["overprint"])
                text_summary[cls.split(" (")[0]] += 1
                min_size = e["size"] if min_size is None else min(min_size, e["size"])
                worrying = (
                    cls.startswith(("rich black", "small", "RGB black", "REGISTRATION", "WHITE"))
                    and e["size"] < 14
                ) or e["size"] < 7 or (cls.startswith("white") and e["size"] < 9) or e["alpha"] < 1 \
                    or (cls.startswith(("RGB", "spot", "CMYK", "rich")) and a.kind == "interior" and a.paper in ("white", "cream"))
                if worrying:
                    key = (cls, round(e["size"]))
                    g = text_flags.setdefault(key, {"colour": cls, "size": e["size"], "count": 0, "pages": [],
                                                    "example": e["text"], "values": [fam, det, val],
                                                    "first_at_in": [inch(e["x"]), inch(e["y"])],
                                                    "opacity": e["alpha"]})
                    g["count"] += 1
                    if page.number + 1 not in g["pages"]:
                        g["pages"].append(page.number + 1)
            else:
                if e["overprint"] and classify(e["fill"], 99, True).startswith("WHITE"):
                    overprint_whites.append(page.number + 1)
                if e["kind"] == "stroke" and 0 < e["width"] < 0.25:
                    thin.append(e["width"])
        if thin:
            hair.append({"page": page.number + 1, "count": len(thin), "thinnest_pt": min(thin)})
        if a.kind == "cover" or page.number < 400:
            cov = ink_coverage(page, dpi=50 if a.kind == "cover" else 20)
            if a.kind == "cover":
                ink.append({"page": page.number + 1, **cov})
            elif has_visible_colour(page):
                colour_pages.append(page.number + 1)
            if a.kind == "interior" and cov["max_tac_pct"] > 240:
                ink.append({"page": page.number + 1, **cov})
        if not runs and not page.get_images() and not page.get_drawings():
            blank_pages.append(page.number + 1)
        edge_hits += [(page.number + 1, *x) for x in text_near_edges(page, runs, trim, a.kind, page.number)]

    R["colour_use"] = dict(colour_use.most_common())
    R["white_objects_set_to_overprint_pages"] = sorted(set(overprint_whites))
    R["text"] = {"min_size_pt": min_size, "colour_classes": dict(text_summary), "flags": list(text_flags.values())}
    R["hairlines_under_0.25pt"] = hair
    R["ink"] = ink
    if a.kind == "interior":
        R["blank_pages"] = blank_pages
        R["pages_with_colour_ink"] = colour_pages[:100]
        if trim:
            R["margins"] = interior_margins(doc, a.pages or len(doc), R.get("interior_bleed") is True)
        if R.get("interior_bleed"):
            gaps = {}
            for pg in doc:
                if pg.get_images() or pg.get_drawings():
                    outside = "right" if pg.number % 2 == 0 else "left"
                    g = bleed_gaps(pg, ("top", "bottom", outside), dpi=72)
                    if g:
                        gaps[pg.number + 1] = g
            R["bleed_gaps_by_page"] = gaps
    if a.kind == "cover":
        R["geometry"] = cover_geometry(doc[0], trim, a.pages, a.paper, a.printer)
        R["bleed_gaps"] = bleed_gaps(doc[0])
        R["text_outside_safe_area"] = [{"page": p, "text": t, "size": s, "why": w} for p, t, s, w in edge_hits]
        R["cover_text"] = doc[0].get_text()[:3000]
        isbns = re.findall(r"97[89][\d\- ]{10,16}", R["cover_text"])
        R["isbns_found_in_text"] = sorted(set(re.sub(r"\D", "", i) for i in isbns))
        R["isbn_checksums_ok"] = {i: isbn13_ok(i) for i in R["isbns_found_in_text"]}

    if a.json:
        with open(a.json, "w") as fh:
            json.dump(R, fh, indent=1, default=str)
    print_report(R)


def print_report(R):
    p = print
    p(f"=== PREFLIGHT FACTS: {R['file']} ({R['kind']}, {R['page_count']} pages) ===")
    d = R["document"]
    p(f"PDF {d['pdf_version']} | PDF/X: {d['gts_pdfx_version'] or 'none declared'} | creator: {d['creator']} | producer: {d['producer']}")
    for oi in d["output_intents"]:
        p(f"  output intent: {oi['condition']} {oi['info']} (ICC embedded: {oi['has_icc']})")
    for k in ("encrypted", "has_layers_ocg", "has_acroform", "has_javascript"):
        if d[k]:
            p(f"  !! {k}")
    p("Page sizes (in): " + ", ".join(f"{s['size']} x{s['count']}" for s in R["page_sizes_in"]))
    if "interior_size_problem" in R:
        p("  !! " + R["interior_size_problem"])
    elif "interior_bleed" in R:
        p(f"  interior bleed: {R['interior_bleed']}")
    if "geometry" in R:
        p("Cover geometry: " + json.dumps(R["geometry"]))
    rs = R["resources"]
    p(f"Colour spaces: {rs['colour_space_kinds']} | ICC types: {rs['icc_profile_types']}")
    p(f"Image colour spaces: {rs['image_colour_spaces']}")
    p(f"Spot colours: {rs['spot_colours'] or 'none'} | DeviceN: {rs['devicen'] or 'none'}")
    for s in R["spot_problems"]:
        p("  !! " + s)
    p(f"Overprint graphics states: {rs['overprint_graphics_states']} | Transparency: {rs['transparency'] or 'none'}")
    p("Fonts:")
    for f in R["fonts"]:
        flag = "" if f["embedded"] else "  !! NOT EMBEDDED"
        p(f"  {f['name']} ({f['type']}) pages {f['pages']}{flag}")
    p("Images (effective ppi at placed size):")
    for im in R["images"][:60]:
        flag = ""
        if im["effective_ppi"] < 300:
            flag += f"  !! under 300ppi"
        if im["upscale_suspect"]:
            flag += f"  !! looks upscaled (detail {im.get('detail_score')})"
        p(f"  p{im['page']} {im['pixels']}px at {im['placed_in']}in = {im['effective_ppi']}ppi, "
          f"{im['colorspace_components']} channels, {im['pct_of_page']}% of page{flag}")
    if len(R["images"]) > 60:
        p(f"  ... {len(R['images']) - 60} more images (see JSON)")
    p("Colour use (object counts): " + ", ".join(f"{k} x{v}" for k, v in list(R["colour_use"].items())[:12]))
    if R["white_objects_set_to_overprint_pages"]:
        p(f"  !! WHITE objects set to overprint (will vanish) on pages {R['white_objects_set_to_overprint_pages'][:20]}")
    t = R["text"]
    p(f"Text: smallest {t['min_size_pt']}pt | colour classes: {t['colour_classes']}")
    for f in t["flags"]:
        pages = f["pages"]
        ptxt = ", ".join(map(str, pages[:8])) + (f" ... ({len(pages)} pages)" if len(pages) > 8 else "")
        p(f"  {f['count']}x {f['size']}pt {f['colour']} {f['values'][2]} on p{ptxt} e.g. '{f['example']}' at {f['first_at_in']}in"
          + (f" opacity {f['opacity']}" if f["opacity"] < 1 else ""))
    for h in R["hairlines_under_0.25pt"]:
        p(f"  !! p{h['page']}: {h['count']} lines under 0.25pt (thinnest {h['thinnest_pt']}pt)")
    for i in R["ink"]:
        p(f"Ink p{i['page']}: max TAC {i['max_tac_pct']}% | area >240%: {i['pct_area_over_240']}% | "
          f">300%: {i['pct_area_over_300']}% | avg CMYK {i['avg_cmyk_pct']}")
    if R["kind"] == "cover":
        for edge, g in R.get("bleed_gaps", {}).items():
            p(f"  !! artwork stops short of the {edge} bleed edge: {g}")
        for e in R["text_outside_safe_area"]:
            p(f"  !! '{e['text']}' ({e['size']}pt): {e['why']}")
        p(f"ISBNs found in cover text: {R['isbns_found_in_text'] or 'none'} | check digit valid: {R['isbn_checksums_ok']}")
    else:
        p(f"Blank pages: {R['blank_pages'][:50]}")
        for pg, g in list(R.get("bleed_gaps_by_page", {}).items())[:20]:
            p(f"  !! p{pg}: art stops short of bleed: {g}")
        if R["pages_with_colour_ink"]:
            p(f"Pages with colour ink: {R['pages_with_colour_ink'][:50]}")
        if "margins" in R:
            m = R["margins"]
            p(f"Margins: need gutter {m['gutter_required_in']}in, outside {m['outside_required_in']}in; "
              f"worst found {m['worst_in']}")
            for o in m["offenders"][:15]:
                p(f"  !! p{o['page']} '{o['text']}' gutter {o['gutter']} outside {o['outside']} top {o['top']} bottom {o['bottom']}")


if __name__ == "__main__":
    main()
