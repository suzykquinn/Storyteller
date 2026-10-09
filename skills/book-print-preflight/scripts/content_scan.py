"""Walk a page's real drawing instructions (like a RIP would) to get true colours.

PyMuPDF reports text colours converted to RGB, which hides the things a printer
cares about (rich black vs 100K, spot vs process, overprint). This interpreter
tracks the graphics state through the content stream, including nested Form
XObjects, and records every text-show and every fill/stroke with its real
colour space, colour values, overprint flag, size and position.
"""
import math
import pikepdf

SHOW_OPS = {"Tj", "TJ", "'", '"'}
PAINT_FILL = {"f", "F", "f*", "B", "B*", "b", "b*"}
PAINT_STROKE = {"S", "s", "B", "B*", "b", "b*"}


def mul(a, b):
    return [a[0]*b[0] + a[1]*b[2], a[0]*b[1] + a[1]*b[3],
            a[2]*b[0] + a[3]*b[2], a[2]*b[1] + a[3]*b[3],
            a[4]*b[0] + a[5]*b[2] + b[4], a[4]*b[1] + a[5]*b[3] + b[5]]


def describe_cs(cs, resources):
    """Return (family, detail) e.g. ('DeviceCMYK', None) or ('Separation', 'PANTONE 186 C')."""
    if isinstance(cs, pikepdf.Name):
        n = str(cs)
        if n in ("/DeviceCMYK", "/DeviceRGB", "/DeviceGray", "/Pattern"):
            return n[1:], None
        try:
            return describe_cs(resources.ColorSpace[n], resources)
        except Exception:
            return n[1:], None
    if isinstance(cs, pikepdf.Array) and len(cs):
        fam = str(cs[0])[1:]
        if fam == "Separation":
            return fam, str(cs[1])[1:]
        if fam == "DeviceN":
            return fam, "+".join(str(x)[1:] for x in cs[1])
        if fam == "ICCBased":
            n = int(cs[1].get("/N", 0))
            return {1: "ICC-Gray", 3: "ICC-RGB", 4: "ICC-CMYK"}.get(n, "ICC"), None
        if fam == "Indexed":
            base, _ = describe_cs(cs[1], resources)
            return "Indexed-" + base, None
        return fam, None
    return "?", None


class State:
    def __init__(self):
        self.ctm = [1, 0, 0, 1, 0, 0]
        self.fill = ("DeviceGray", None, (0.0,))
        self.stroke = ("DeviceGray", None, (0.0,))
        self.op_fill = False
        self.op_stroke = False
        self.font_size = 0
        self.line_width = 1.0
        self.alpha = 1.0

    def copy(self):
        s = State()
        s.__dict__.update({k: (list(v) if isinstance(v, list) else v) for k, v in self.__dict__.items()})
        return s


def scan_page(pdf_page, page_height):
    events = []
    resources = pdf_page.obj.get("/Resources", pikepdf.Dictionary())
    _scan(pdf_page.obj, resources, State(), events, page_height, depth=0)
    return events


def _scan(stream_owner, resources, st, events, H, depth):
    if depth > 12:
        return
    stack = []
    tm = [1, 0, 0, 1, 0, 0]
    tlm = [1, 0, 0, 1, 0, 0]
    leading = 0
    try:
        ops = pikepdf.parse_content_stream(stream_owner)
    except Exception:
        return
    cur_fill_cs = st.fill[:2]
    cur_stroke_cs = st.stroke[:2]
    for operands, op in ops:
        op = str(op)
        try:
            if op == "q":
                stack.append(st.copy())
            elif op == "Q":
                if stack:
                    st = stack.pop()
                    cur_fill_cs, cur_stroke_cs = st.fill[:2], st.stroke[:2]
            elif op == "cm":
                st.ctm = mul([float(x) for x in operands], st.ctm)
            elif op == "w":
                st.line_width = float(operands[0])
            elif op == "gs":
                gs = resources.ExtGState[operands[0]]
                if "/OP" in gs:
                    st.op_stroke = bool(gs.OP)
                    st.op_fill = bool(gs.get("/op", gs.OP))
                if "/op" in gs:
                    st.op_fill = bool(gs.op)
                if "/ca" in gs:
                    st.alpha = float(gs.ca)
            # ---- colours
            elif op in ("g", "G", "rg", "RG", "k", "K"):
                fam = {"g": "DeviceGray", "rg": "DeviceRGB", "k": "DeviceCMYK"}[op.lower()]
                val = (fam, None, tuple(round(float(x), 3) for x in operands))
                if op.islower():
                    st.fill = val; cur_fill_cs = val[:2]
                else:
                    st.stroke = val; cur_stroke_cs = val[:2]
            elif op in ("cs", "CS"):
                fam, det = describe_cs(operands[0], resources)
                if op == "cs":
                    cur_fill_cs = (fam, det); st.fill = (fam, det, (1.0,))
                else:
                    cur_stroke_cs = (fam, det); st.stroke = (fam, det, (1.0,))
            elif op in ("sc", "scn", "SC", "SCN"):
                vals = tuple(round(float(x), 3) for x in operands if not isinstance(x, pikepdf.Name))
                if op.islower():
                    st.fill = (*cur_fill_cs, vals)
                else:
                    st.stroke = (*cur_stroke_cs, vals)
            # ---- text
            elif op == "BT":
                tm = [1, 0, 0, 1, 0, 0]; tlm = [1, 0, 0, 1, 0, 0]
            elif op == "Tf":
                st.font_size = float(operands[1])
            elif op == "TL":
                leading = float(operands[0])
            elif op == "Tm":
                tm = [float(x) for x in operands]; tlm = list(tm)
            elif op in ("Td", "TD"):
                tx, ty = float(operands[0]), float(operands[1])
                if op == "TD":
                    leading = -ty
                tlm = mul([1, 0, 0, 1, tx, ty], tlm); tm = list(tlm)
            elif op == "T*":
                tlm = mul([1, 0, 0, 1, 0, -leading], tlm); tm = list(tlm)
            elif op in SHOW_OPS:
                if op in ("'", '"'):
                    tlm = mul([1, 0, 0, 1, 0, -leading], tlm); tm = list(tlm)
                m = mul(tm, st.ctm)
                scale = math.sqrt(abs(m[0]*m[3] - m[1]*m[2]))
                raw = b""
                for o in operands:
                    if isinstance(o, pikepdf.String):
                        raw += bytes(o)
                    elif isinstance(o, pikepdf.Array):
                        raw += b"".join(bytes(x) for x in o if isinstance(x, pikepdf.String))
                txt = raw.decode("latin-1", "replace")
                if sum(c.isprintable() for c in txt) < 0.8 * max(1, len(txt)):
                    txt = "(encoded text)"
                events.append({"kind": "text", "size": round(st.font_size * scale, 2),
                               "fill": st.fill, "overprint": st.op_fill, "alpha": st.alpha,
                               "x": round(m[4], 1), "y": round(H - m[5], 1), "text": txt[:60]})
            # ---- painting
            elif op in PAINT_FILL or op in PAINT_STROKE:
                if op in PAINT_FILL:
                    events.append({"kind": "fill", "fill": st.fill, "overprint": st.op_fill})
                if op in PAINT_STROKE:
                    sc = math.sqrt(abs(st.ctm[0]*st.ctm[3] - st.ctm[1]*st.ctm[2]))
                    events.append({"kind": "stroke", "fill": st.stroke, "overprint": st.op_stroke,
                                   "width": round(st.line_width * sc, 3)})
            elif op == "Do":
                xo = resources.XObject[operands[0]]
                if xo.get("/Subtype") == "/Form":
                    child = st.copy()
                    if "/Matrix" in xo:
                        child.ctm = mul([float(x) for x in xo.Matrix], st.ctm)
                    _scan(xo, xo.get("/Resources", resources), child, events, H, depth + 1)
        except Exception:
            continue


def classify(fill, size, overprint):
    """Plain-English verdict for a text colour."""
    fam, det, v = fill
    if fam in ("Separation",):
        if det and det.lower() == "all":
            return "REGISTRATION colour (prints on every plate)"
        return f"spot colour {det}"
    if fam == "DeviceN":
        return f"DeviceN {det}"
    if fam in ("DeviceCMYK", "ICC-CMYK") and len(v) == 4:
        C, M, Y, K = v
        tot = C + M + Y + K
        if tot < 0.02:
            return "WHITE set to OVERPRINT (will disappear)" if overprint else "white"
        if K >= 0.95 and C + M + Y > 0.05:
            return f"rich black {round(tot*100)}% ({C:.0%}/{M:.0%}/{Y:.0%}/{K:.0%})"
        if K >= 0.95:
            return "100K black" + (" (overprints, good)" if overprint else " (knocks out)")
        inks = sum(1 for x in (C, M, Y, K) if x > 0.05)
        if inks >= 3 and size < 10:
            return f"small {inks}-colour text, registration risk"
        return f"CMYK {round(tot*100)}%"
    if fam in ("DeviceRGB", "ICC-RGB"):
        if all(x > 0.98 for x in v):
            return "white (RGB)"
        if all(x < 0.02 for x in v):
            return "RGB black (converts to 4-colour rich black)"
        return "RGB colour"
    if fam in ("DeviceGray", "ICC-Gray"):
        g = v[0] if v else 0
        if g > 0.98:
            return "WHITE set to OVERPRINT (will disappear)" if overprint else "white"
        return "grey/black (K only)"
    return fam
