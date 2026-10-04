"""Compose views.json into the standard-views drawing sheet."""
import json, math
import model_v2 as M

V = json.load(open("views.json"))
out = []
w = out.append


def line(x1, y1, x2, y2, cls="thin", extra=""):
    w(f'<line class="{cls}" x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" {extra}/>')


def text(x, y, s, cls="t", anchor="start", rot=None):
    tr = f' transform="rotate({rot} {x:.2f} {y:.2f})"' if rot is not None else ""
    w(f'<text class="{cls}" x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}"{tr}>{s}</text>')


def leader(px, py, tx, ty, lines, anchor="start", cls="ts"):
    line(tx, ty, px, py, "dim", 'marker-end="url(#ah)"')
    sx = tx + (6 if anchor == "start" else -6)
    for i, s in enumerate(lines):
        text(sx, ty + 5 + i * 16, s, cls, anchor)


def view_title(x, y, a, *subs):
    text(x, y, a, "vt", "middle")
    for i, b in enumerate(subs):
        text(x, y + 20 + i * 17, b, "vs", "middle")


def draw(view, cx, cy, s, cls="vl", center=None):
    pls = V[view]["vis"]
    xs = [x for pl in pls for x, _ in pl]; ys = [y for pl in pls for _, y in pl]
    mx, my = center if center else ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    d = []
    for pl in pls:
        d.append("M" + " L".join(f"{cx + s*(x-mx):.1f},{cy - s*(y-my):.1f}" for x, y in pl))
    w(f'<path class="{cls}" d="{" ".join(d)}"/>')
    return (cx + s * (min(xs) - mx), cx + s * (max(xs) - mx),
            cy - s * (max(ys) - my), cy - s * (min(ys) - my))


W, H = 1600, 1130
w(f'<svg class="sheet" viewBox="0 0 {W} {H}" role="img" aria-label="Standard engineering views of the v2 compliant spur gear: top, front, right side, isometric, and an isometric detail of one tooth showing the interleaved 45-degree wedge fingers at the tip.">')
w('<defs><marker id="ah" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,1.5 L10,5 L0,8.5 Z" class="ahf"/></marker></defs>')
w(f'<rect class="paper" x="0" y="0" width="{W}" height="{H}"/>')
w(f'<rect class="frame" x="14" y="14" width="{W-28}" height="{H-28}"/>')
for i in range(1, 8):
    x = 14 + i * (W - 28) / 8
    line(x, 14, x, 24); line(x, H - 24, x, H - 14)
    text(x - (W - 28) / 16, 23, str(i), "zone", "middle")
for i, ch in enumerate("ABCD"):
    text(21, 14 + (i + 0.5) * (H - 28) / 4 + 4, ch, "zone", "middle")

s = 5.0
ra, rp, F, B = M.ra, M.rp, M.F, M.BORE

# ---- TOP (gear face) ----
cx, cy = 290, 285
draw("top", cx, cy, s)
w(f'<circle class="ctr nofill" cx="{cx}" cy="{cy}" r="{s*rp}"/>')
line(cx - s * ra - 18, cy, cx + s * ra + 18, cy, "ctr")
line(cx, cy - s * ra - 18, cx, cy + s * ra + 18, "ctr")
yd = cy - s * ra - 36
for x in (cx - s * ra, cx + s * ra):
    line(x, cy - 4, x, yd - 6, "ext")
line(cx - s * ra, yd, cx + s * ra, yd, "dim", 'marker-start="url(#ah)" marker-end="url(#ah)"')
text(cx, yd - 7, "Ø66.00", "t", "middle")
leader(cx + s * B / 2 * 0.7, cy - s * B / 2 * 0.7, cx + 190, cy - 190, ["Ø8.00 THRU"])
a = math.radians(225)
leader(cx + s * rp * math.cos(a), cy - s * rp * math.sin(a), 52, 478, ["PCD Ø60.00"])
# detail A marker on the tooth at -36 deg
ang = math.radians(-36)
dx, dy = cx + s * (ra - 3) * math.cos(ang), cy - s * (ra - 3) * math.sin(ang)
w(f'<circle class="thin nofill dash" cx="{dx:.1f}" cy="{dy:.1f}" r="26"/>')
text(dx + 22, dy + 34, "A", "tag")
view_title(cx, 512, "TOP VIEW", "SCALE 1:1")

# ---- FRONT ----
fx, fy = 290, 625
draw("front", fx, fy, s)
for xx in (-B / 2, B / 2):
    line(fx + s * xx, fy - s * F / 2, fx + s * xx, fy + s * F / 2, "hid")
line(fx, fy - s * F / 2 - 14, fx, fy + s * F / 2 + 14, "ctr")
xd = fx - s * ra - 30
for yy in (fy - s * F / 2, fy + s * F / 2):
    line(fx - s * ra - 4, yy, xd - 6, yy, "ext")
line(xd, fy - s * F / 2, xd, fy + s * F / 2, "dim", 'marker-start="url(#ah)" marker-end="url(#ah)"')
text(xd - 8, fy, "12.00", "t", "middle", rot=-90)
view_title(fx, 700, "FRONT VIEW", "SCALE 1:1")
# projection link lines (top -> front)
for x in (fx - s * ra, fx + s * ra):
    line(x, cy + s * ra + 22, x, fy - s * F / 2 - 6, "ext", 'stroke-dasharray="2 5"')

# ---- RIGHT ----
rx, ry = 720, 625
draw("right", rx, ry, s)
for xx in (-B / 2, B / 2):
    line(rx + s * xx, ry - s * F / 2, rx + s * xx, ry + s * F / 2, "hid")
line(rx, ry - s * F / 2 - 14, rx, ry + s * F / 2 + 14, "ctr")
line(fx + s * ra + 22, fy - s * F / 2, rx - s * ra - 6, ry - s * F / 2, "ext", 'stroke-dasharray="2 5"')
line(fx + s * ra + 22, fy + s * F / 2, rx - s * ra - 6, ry + s * F / 2, "ext", 'stroke-dasharray="2 5"')
view_title(rx, 700, "RIGHT VIEW", "SCALE 1:1")

# ---- ISO ----
draw("iso", 720, 280, s)
view_title(720, 512, "ISOMETRIC VIEW", "SCALE 1:1")

# ---- DETAIL A ----
b = draw("detail", 1290, 330, 22.0, "vl2")
view_title(1290, 640, "DETAIL A", "ISOMETRIC · SCALE 4.4:1 · ONE TOOTH, CROPPED")
text(1290, 690, "WEDGE FINGERS: 4 FROM WALL L, 4 FROM WALL R, 45° FACES.", "ts", "middle")
text(1290, 707, "TIPS STOP 1.00 SHORT OF THE OPPOSITE WALL.", "ts", "middle")

# ---- GEAR DATA ----
tx0, ty0, rh = 40, 760, 25
cols = [(40, 180, 90), (320, 180, 90)]
rows = [("TEETH", "20"), ("MODULE", "3.000"), ("PRESSURE ANGLE", "20°"), ("PITCH DIA", "60.000"),
        ("TIP DIA", "66.000"), ("ROOT DIA", "52.500"), ("FACE WIDTH", "12.000"), ("BORE", "Ø8.000"),
        ("PRELOAD / FLANK", "0.100"), ("WALL THK @ PCD", "1.11"), ("CAP HEIGHT", "1.80"),
        ("FINGER CLEARANCE", "1.00"), ("WEDGE ANGLE", "45°"), ("WEDGE PERIOD", "3.00"),
        ("MATING PINION", "16T m3"), ("CENTRE DIST.", "54.000")]
half = len(rows) // 2
text(40, ty0 - 8, "GEAR DATA", "th")
for c, (x0, c1, c2) in enumerate(cols):
    sub = rows[c * half:(c + 1) * half]
    w(f'<rect class="tbl" x="{x0}" y="{ty0}" width="{c1+c2}" height="{rh*len(sub)}"/>')
    line(x0 + c1, ty0, x0 + c1, ty0 + rh * len(sub))
    for i, (k, v) in enumerate(sub):
        y = ty0 + rh * i
        if i: line(x0, y, x0 + c1 + c2, y)
        text(x0 + 8, y + 17, k, "td")
        text(x0 + c1 + c2 - 8, y + 17, v, "tdv", "end")

# ---- NOTES ----
nx, ny = 990, 752
text(nx, ny - 8, "NOTES", "th")
notes = [
    "1. ALL DIMENSIONS IN MM. THIRD-ANGLE PROJECTION.",
    "2. SOURCE: compliant_gear_v2.scad (DEFAULT PARAMETERS).",
    "3. VIEWS ARE HIDDEN-LINE PROJECTIONS OF AN EXACT B-REP;",
    "    VOLUME MATCHES THE EXPORTED STL TO 0.04%.",
    "4. HIDDEN LINES SHOWN FOR THE BORE ONLY.",
    "5. PRINT FLAT ON EITHER FACE; THE FINGER CAP IS",
    "    SELF-SUPPORTING (ALL DOWN-FACING SURFACES ≤ 45°).",
    "6. GEAR TEETH CUT 0.10 OVERSIZE PER FLANK FOR PRELOAD.",
]
for i, s_ in enumerate(notes):
    text(nx, ny + 16 + i * 18, s_, "tn")

# ---- TITLE BLOCK ----
bx, by = 980, 900
bx2 = W - 14
w(f'<rect class="tbl" x="{bx}" y="{by}" width="{bx2-bx}" height="{H-14-by}"/>')
line(bx, by + 92, bx2, by + 92); line(bx, by + 140, bx2, by + 140)
for xx in (bx + 150, bx + 300, bx + 450):
    line(xx, by + 92, xx, H - 14)
text(bx + 14, by + 26, "TITLE", "tk")
text(bx + 14, by + 58, "COMPLIANT ZERO-BACKLASH SPUR GEAR", "ttl")
text(bx + 14, by + 80, "V2 · STANDARD VIEWS", "tv")
cells = [("DWG NO.", "CG-M3-20-V2"), ("REV", "A"), ("SCALE", "1:1 U.O.N."), ("SHEET", "1 / 1"),
         ("MATERIAL", "RESIN / PETG"), ("UNITS", "MM"), ("DRAWN", "CLAUDE"), ("DATE", "2026-10-03")]
for i, (k, v) in enumerate(cells):
    x = bx + (i % 4) * 150 + 10; y = by + 92 + (i // 4) * 48
    text(x, y + 16, k, "tk"); text(x, y + 38, v, "tv")
w('</svg>')

html = open("template.html").read().replace("%%SVG%%", "\n".join(out))
open("compliant-gear-v2-views.html", "w").write(html)
print("ok", b)
