# Generates the engineering drawing (inline SVG in HTML). Parameters mirror
# ../compliant_gear.scad; keep them in sync.  Usage: python3 drawing/gen.py
import math

# ---------------- parameters (mirror compliant_gear.scad) ----------------
m, N, F, PA, BORE = 3.0, 20, 12.0, 20.0, 8.0
PRELOAD, HF, SLOT_D = 0.10, 0.55, 2.0
CAP_H, LAYERS, CLR, ZG = 1.8, 4, 1.0, 0.3
N2 = 16
rp = m * N / 2
rb = rp * math.cos(math.radians(PA))
ra = rp + m
rf = rp - 1.25 * m
rcap = ra - CAP_H
inv = lambda a: math.tan(a) - a


def psi(r, pl=PRELOAD):
    rr = max(r, rb)
    return math.pi / (2 * N) + pl / rp + inv(math.radians(PA)) - inv(math.acos(rb / rr))


sa = lambda r: HF * psi(min(r, ra))        # slot half angle
HW = rf * sa(rf)
T_HALF = rp * psi(rp)
S_HALF = rp * sa(rp)
WALL = T_HALF - S_HALF
TOOTH_NOM = math.pi * m / 2
y0 = rf - SLOT_D                            # cantilever root (slot bottom centre)
E = 3500.0
Lp = rp - y0
K = 3 * E * (F * WALL ** 3 / 12) / Lp ** 3  # N/mm at pitch
ratio = (3 * (ra - y0) - Lp) / (2 * Lp)     # tip deflection / pitch deflection
D_TIP_STOP = CLR / 2
D_PCD_STOP = D_TIP_STOP / ratio


def layer_z(i):
    za = i * F / LAYERS + (ZG / 2 if i > 0 else 0)
    zb = (i + 1) * F / LAYERS - (ZG / 2 if i < LAYERS - 1 else 0)
    return za, zb


side_of = lambda i: 1 if i % 2 == 0 else -1   # +1: finger from wall L

# ---------------- tooth contours in local frame ----------------
# local: x = r sin a (tangential, + = CCW seen from +z = wall L), y = r cos a
P = lambda r, a: (r * math.sin(a), r * math.cos(a))


def rng(a, b, n=28):
    return [a + (b - a) * i / n for i in range(n + 1)]


def arc(r, a0, a1, n=10):
    return [P(r, a) for a in rng(a0, a1, n)]


def flank(sign, r_from, r_to, pl=PRELOAD):
    return [P(r, sign * psi(r, pl)) for r in rng(r_from, r_to)]


def slot_edge(sign, r_from, r_to):
    return [P(r, sign * sa(r)) for r in rng(r_from, r_to)]


def finger_end(sign, r_from, r_to):
    # end face of the finger coming from wall `-sign`, lying near wall `sign`
    return [P(r, sign * (sa(r) - CLR / r)) for r in rng(r_from, r_to, 12)]


def slot_bottom():
    pts = [(-HW, rf), (-HW, y0)]
    pts += [(HW * math.cos(t), y0 + HW * math.sin(t)) for t in rng(math.pi, 2 * math.pi, 16)]
    pts += [(HW, rf)]
    return pts


HP = math.pi / N


def tag(pts, o):
    return [(x, y, o) for (x, y) in pts]


def contour(layer):
    """material contour for a finger layer ('L' = finger from wall L), tagged
    with owner +1 (wall L) / -1 (wall R) / 0 (rim). Runs root -HP -> +HP."""
    if layer == "R":
        return [(-x, y, -o) for (x, y, o) in reversed(contour("L"))]
    c = []
    c += tag(arc(rf, -HP, -psi(rf)), 0)
    c += tag(flank(-1, rf, ra), -1)
    c += tag(arc(ra, -psi(ra), -sa(ra), 4), -1)
    c += tag(slot_edge(-1, ra, rf), -1)
    c += [(x, y, 0) for (x, y) in slot_bottom()]
    c += tag(slot_edge(1, rf, rcap), 1)
    c += tag(finger_end(-1, rcap, ra), 1)
    c += tag(arc(ra, -(sa(ra) - CLR / ra), psi(ra), 8), 1)
    c += tag(flank(1, ra, rf), 1)
    c += tag(arc(rf, psi(rf), HP), 0)
    return c


def silhouette():
    """union of all layers: outer tooth (cap closed) and the hole below the cap"""
    outer = arc(rf, -HP, -psi(rf)) + flank(-1, rf, ra) + arc(ra, -psi(ra), psi(ra), 12) \
        + flank(1, ra, rf) + arc(rf, psi(rf), HP)
    hole = slot_edge(-1, rcap, rf) + slot_bottom() + slot_edge(1, rf, rcap)
    return outer, hole


def window(pts, rbot):
    a = HP
    return pts + [P(rbot / math.cos(a), a), P(rbot / math.cos(a), -a)]


def deflect(c, d_tip):
    """walls bent toward the centre; cantilever shape from slot bottom"""
    out_ = []
    for (x, y, o) in c:
        f = max(0.0, (y - y0) / (ra - y0)) ** 2
        out_.append((x - o * d_tip * f, y))
    return out_


xy = lambda c: [(x, y) for (x, y, _) in c]

# ---------------- svg helpers ----------------
out = []
w = out.append


def poly(pts, cls, closed=True):
    d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + (" Z" if closed else "")
    w(f'<path class="{cls}" d="{d}"/>')


def line(x1, y1, x2, y2, cls="thin", extra=""):
    w(f'<line class="{cls}" x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" {extra}/>')


def text(x, y, s, cls="t", anchor="start", rot=None):
    tr = f' transform="rotate({rot} {x:.2f} {y:.2f})"' if rot is not None else ""
    w(f'<text class="{cls}" x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}"{tr}>{s}</text>')


def dimh(x1, x2, y, s, ext=None, outside=False, tpos=None, cls="t"):
    for (ex, ey) in (ext or []):
        d = 1 if y > ey else -1
        line(ex, ey + 4 * d, ex, y + 6 * d, "ext")
    a, b = min(x1, x2), max(x1, x2)
    if outside:
        line(a - 26, y, a, y, "dim", 'marker-end="url(#ah)"')
        line(b + 26, y, b, y, "dim", 'marker-end="url(#ah)"')
        line(a, y, b, y, "dim")
    else:
        line(a, y, b, y, "dim", 'marker-start="url(#ah)" marker-end="url(#ah)"')
    tx = tpos if tpos is not None else (a + b) / 2
    text(tx, y - 7, s, cls, "middle")


def dimv(x, y1, y2, s, ext=None, outside=False, tside=-1):
    for (ex, ey) in (ext or []):
        d = 1 if x > ex else -1
        line(ex + 4 * d, ey, x + 6 * d, ey, "ext")
    a, b = min(y1, y2), max(y1, y2)
    if outside:
        line(x, a - 20, x, a, "dim", 'marker-end="url(#ah)"')
        line(x, b + 20, x, b, "dim", 'marker-end="url(#ah)"')
        line(x, a, x, b, "dim")
    else:
        line(x, a, x, b, "dim", 'marker-start="url(#ah)" marker-end="url(#ah)"')
    tx = x - 7 if tside < 0 else x + 17
    text(tx, (a + b) / 2, s, "t", "middle", rot=-90)


def leader(px, py, tx, ty, lines, anchor="start", cls="ts"):
    line(tx, ty, px, py, "dim", 'marker-end="url(#ah)"')
    sx = tx + (6 if anchor == "start" else -6)
    for i, s in enumerate(lines):
        text(sx, ty + 5 + i * 16, s, cls, anchor)


def view_title(x, y, a, *subs):
    text(x, y, a, "vt", "middle")
    for i, b in enumerate(subs):
        text(x, y + 20 + i * 17, b, "vs", "middle")


# ---------------- sheet ----------------
W, H = 1600, 1130
w(f'<svg class="sheet" viewBox="0 0 {W} {H}" role="img" aria-label="Engineering drawing of a compliant zero-backlash spur gear: 20 teeth, module 3. Each tooth is two full-width spring walls; the tip is closed by four interleaved finger layers that slide past each other until a finger reaches the opposite wall after 1.00 mm of closing travel.">')
w('<defs>'
  '<marker id="ah" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,1.5 L10,5 L0,8.5 Z" class="ahf"/></marker>'
  '<marker id="ahb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="16" markerHeight="16" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L10,5 L0,10 Z" class="ahacc"/></marker>'
  '<pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" class="hl"/></pattern>'
  '<pattern id="hatchacc" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><line x1="0" y1="0" x2="0" y2="6" class="hla"/></pattern>'
  '</defs>')
w(f'<rect class="paper" x="0" y="0" width="{W}" height="{H}"/>')
w(f'<rect class="frame" x="14" y="14" width="{W-28}" height="{H-28}"/>')
for i in range(1, 8):
    x = 14 + i * (W - 28) / 8
    line(x, 14, x, 24, "thin"); line(x, H - 24, x, H - 14, "thin")
    text(x - (W - 28) / 16, 23, str(i), "zone", "middle")
for i, ch in enumerate("ABCD"):
    y = 14 + (i + 0.5) * (H - 28) / 4
    text(21, y + 4, ch, "zone", "middle")

# ======== FRONT VIEW (1:1, 5 px/mm) ========
sF = 5.0
cx, cy = 212, 280
def TF(pt, rot):
    x, y = pt
    c, s = math.cos(rot), math.sin(rot)
    gx, gy = x * c - y * s, x * s + y * c
    return (cx - sF * gx, cy - sF * gy)
o_pts, h_pts = silhouette()
full = []
for i in range(N):
    rot = -i * 2 * math.pi / N
    full += [TF(p, rot) for p in o_pts]
    poly([TF(p, rot) for p in h_pts], "vis")
poly(full, "vis")
w(f'<circle class="vis nofill" cx="{cx}" cy="{cy}" r="{sF*BORE/2}"/>')
w(f'<circle class="ctr nofill" cx="{cx}" cy="{cy}" r="{sF*rp}"/>')
line(cx - sF * ra - 16, cy, cx + sF * ra + 16, cy, "ctr")
line(cx, cy - sF * ra - 16, cx, cy + sF * ra + 16, "ctr")
dcx, dcy, dr = cx, cy - sF * 29.3, sF * 5.6
w(f'<circle class="thin nofill dash" cx="{dcx}" cy="{dcy:.2f}" r="{dr}"/>')
text(dcx + dr + 4, dcy - dr + 6, "D", "tag")
dimh(cx - sF * ra, cx + sF * ra, cy - sF * ra - 34, "Ø66.00 TIP",
     ext=[(cx - sF * ra, cy - 2), (cx + sF * ra, cy - 2)])
a = math.radians(222)
leader(cx + sF * rf * math.cos(a), cy - sF * rf * math.sin(a), 46, 470, ["Ø52.50 ROOT"])
a = math.radians(-35)
leader(cx + sF * rp * math.cos(a), cy - sF * rp * math.sin(a), 318, 482, ["PCD Ø60.00"])
leader(cx + sF * BORE / 2 * 0.7, cy - sF * BORE / 2 * 0.7, cx + 140, cy - 178, ["Ø8.00 BORE"])
view_title(cx, 540, "FRONT VIEW", "SCALE 1:1 · SILHOUETTE, CAP CLOSED")

# ======== DETAIL D = SECTION A-A (8:1, 40 px/mm) ========
sD = 40.0
dX, dY, rtop = 700, 92, 33.6
TD = lambda p: (dX - sD * p[0], dY + sD * (rtop - p[1]))
rbot = y0 - HW - 0.7
cA = contour("L")
poly([TD(p) for p in window(xy(cA), rbot)], "sec")
# finger of this layer emphasised
fing = slot_edge(1, rcap, ra) + list(reversed(finger_end(-1, rcap, ra)))
poly([TD(p) for p in fing], "pad")
# other layer's finger, phantom
poly([TD((-x, y)) for (x, y) in fing], "phantom")
for sg in (-1, 1):
    poly([TD(p) for p in flank(sg, rf + 0.4, ra, 0.0)], "phantom", False)
poly([TD(P(rp, a)) for a in rng(-HP * 1.05, HP * 1.05, 40)], "ctr", False)
line(dX, dY - 14, dX, TD((0, rbot - 0.4))[1], "ctr")
xt, yt = TD(P(rp, -HP * 1.05)); text(xt + 6, yt + 5, "PCD", "ts")
# finger clearance dim
ea = TD(P(ra, -sa(ra))); eb = TD(P(ra, -(sa(ra) - CLR / ra)))
dimh(ea[0], eb[0], 70, "1.00", ext=[ea, eb], outside=True, tpos=(ea[0] + eb[0]) / 2 + 52)
# cap height dim (right of window)
xr = TD(P(rf, -HP))[0] + 34
dimv(xr, TD((0, rcap))[1], TD((0, ra))[1], "1.80 CAP", tside=1,
     ext=[(TD(P(rcap, -psi(rcap)))[0], TD((0, rcap))[1]), (TD(P(ra, -psi(ra)))[0], TD((0, ra))[1])])
text(TD(P(ra, psi(ra) * 0.7))[0], TD((0, ra))[1] - 12, "L", "tag", "middle")
text(TD(P(ra, -psi(ra) * 0.7))[0], TD((0, ra))[1] - 12, "R", "tag", "middle")
px, py = TD(P(rcap + 0.6, 0.004))
leader(px, py, 905, 150, ["FINGER FROM WALL L", "(LAYERS 1, 3)"])
px, py = TD(P(rcap + 0.5, -sa(rcap + 0.5) + 0.3 / (rcap + 0.5)))
leader(px, py, 905, 215, ["FINGER FROM WALL R", "(LAYERS 2, 4) PHANTOM"])
px, py = TD(P(31.0, psi(31.0, 0.0)))
leader(px, py, 528, 150, ["NOMINAL FLANK", "(PHANTOM)"], "end")
px, py = TD(P(29.0, psi(29.0)))
leader(px, py, 528, 245, ["0.10 OVERSIZE", "PER FLANK @ PCD"], "end")
px, py = TD((HW * 0.7, y0 - HW * 0.7))
leader(px, py, 528, 405, [f"SLOT R{HW:.2f}", "2.00 BELOW ROOT"], "end")
px, py = TD(P(rf, HP * 0.8))
leader(px, py, 528, 470, ["ROOT Ø52.50", "FILLETS R0.60"], "end")
view_title(dX, 572, "DETAIL D · SECTION A-A", "SCALE 8:1 · LAYER 1, Z 0–2.85")

# ======== SECTION B-B and AT-STOP view (4:1, 20 px/mm) ========
sS = 20.0
def TSf(sx):
    return lambda p: (sx - sS * p[0], 92 + sS * (rtop - p[1]))
TS = TSf(1030)
cB = contour("R")
poly([TS(p) for p in window(xy(cB), rbot)], "sec")
line(1030, 80, 1030, TS((0, rbot - 0.4))[1], "ctr")
text(TS(P(ra, psi(ra) * 0.7))[0], TS((0, ra))[1] - 10, "L", "tag", "middle")
text(TS(P(ra, -psi(ra) * 0.7))[0], TS((0, ra))[1] - 10, "R", "tag", "middle")
view_title(1030, 365, "SECTION B-B", "LAYER 2, Z 3.15–5.85", "FINGER FROM WALL R")

TS2 = TSf(1205)
dA = deflect(cA, D_TIP_STOP)
dB = deflect(cB, D_TIP_STOP)
poly([TS2(p) for p in window(dA, rbot)], "sec")
poly([TS2(p) for p in window(dB, rbot)], "hid")
for sg in (-1, 1):
    poly([TS2(p) for p in flank(sg, rf, ra)], "phantom", False)
line(1205, 80, 1205, TS2((0, rbot - 0.4))[1], "ctr")
for (sg, z) in ((1, 0), (-1, 0)):
    x0 = TS2(P(rp, sg * psi(rp)))
    xa = x0[0] - sg * 34
    line(xa, x0[1], x0[0] - sg * 3, x0[1], "load", 'marker-end="url(#ahb)"')
view_title(1205, 365, "AT CONTACT", f"TIP {D_TIP_STOP:.2f} / WALL",
           "A-A SOLID", "B-B DASHED")
text(1117, 440, "PHANTOM = FLANKS AT REST.", "ts", "middle")
text(1117, 457, "FINGERS HAVE PASSED; EACH TOUCHES THE", "ts", "middle")
text(1117, 474, "OPPOSITE WALL. NO SEPARATE STOP.", "ts", "middle")

# ======== GEAR DATA TABLE ========
tx0, ty0, cw1, cw2, rh = 1310, 50, 178, 92, 25
rows = [
    ("NUMBER OF TEETH", "20"), ("MODULE", "3.000"), ("PRESSURE ANGLE", "20°"),
    ("PITCH DIA", f"{2*rp:.3f}"), ("BASE DIA", f"{2*rb:.3f}"), ("TIP DIA", f"{2*ra:.3f}"),
    ("ROOT DIA", f"{2*rf:.3f}"), ("FACE WIDTH", f"{F:.3f}"),
    ("TOOTH THK @ PCD", f"{2*T_HALF:.3f}"), ("  NOMINAL", f"{TOOTH_NOM:.3f}"),
    ("PRELOAD / FLANK", f"{PRELOAD:.3f}"), ("WALL THK @ PCD", f"{WALL:.2f}"),
    ("SLOT WIDTH @ PCD", f"{2*S_HALF:.2f}"), ("CAP LAYERS", f"{LAYERS}"),
    ("FINGER CLEARANCE", f"{CLR:.2f}"), ("TRAVEL @ PCD", f"{D_PCD_STOP:.2f}"),
    ("MATING PINION", f"{N2}T m3"), ("CENTRE DIST.", f"{m*(N+N2)/2:.3f}"),
]
w(f'<rect class="tbl" x="{tx0}" y="{ty0}" width="{cw1+cw2}" height="{rh*(len(rows)+1)}"/>')
text(tx0 + (cw1 + cw2) / 2, ty0 + 17, "GEAR DATA", "th", "middle")
for i, (k, v) in enumerate(rows):
    y = ty0 + rh * (i + 1)
    line(tx0, y, tx0 + cw1 + cw2, y, "thin")
    text(tx0 + 8, y + 17, k, "td")
    text(tx0 + cw1 + cw2 - 8, y + 17, v, "tdv", "end")
line(tx0 + cw1, ty0 + rh, tx0 + cw1, ty0 + rh * (len(rows) + 1), "thin")

# ======== SECTION F-F (developed through the cap, 10:1, 50 px/mm) ========
rm = ra - CAP_H / 2
sP = 25.0
fx, fy = 235, 1000
TPu = lambda u: fx - sP * u
TPz = lambda z: fy - sP * z
Tm, Sm = rm * psi(rm), rm * sa(rm)
Uw = Tm + 1.4
def comb(sg):
    """wall + its fingers, developed; sg=+1 wall L"""
    pts = [(sg * Tm, 0), (sg * Tm, F)]
    edge = []
    for i in reversed(range(LAYERS)):
        za, zb = layer_z(i)
        if side_of(i) == sg:
            edge += [(sg * Sm, zb), (-sg * (Sm - CLR), zb), (-sg * (Sm - CLR), za), (sg * Sm, za)]
    return pts + [(sg * Sm, F)] + edge + [(sg * Sm, 0)]
for sg in (1, -1):
    poly([(TPu(u), TPz(z)) for (u, z) in comb(sg)], "sec")
    for i in range(LAYERS):
        if side_of(i) == sg:
            za, zb = layer_z(i)
            poly([(TPu(sg * Sm), TPz(za)), (TPu(-sg * (Sm - CLR)), TPz(za)),
                  (TPu(-sg * (Sm - CLR)), TPz(zb)), (TPu(sg * Sm), TPz(zb))], "pad")
for z in (0, F):
    line(TPu(Uw), TPz(z), TPu(-Uw), TPz(z), "thin")
line(fx, TPz(-0.8), fx, TPz(F + 0.8), "ctr")
for (u, sg) in ((Uw - 0.1, 1), (-(Uw - 0.1), -1)):
    for z in (3.0, 9.0):
        line(TPu(u), TPz(z), TPu(sg * (Tm + 0.12)), TPz(z), "load", 'marker-end="url(#ahb)"')
text(TPu(Uw), TPz(F) - 8, "LOAD", "tsacc")
text(TPu(-Uw), TPz(F) - 8, "LOAD", "tsacc", "end")
text(TPu(Tm / 2 + Sm / 2), TPz(0) + 28, "L", "tag", "middle")
text(TPu(-(Tm / 2 + Sm / 2)), TPz(0) + 28, "R", "tag", "middle")
# cutting planes
for (i, ch) in ((0, "A"), (1, "B")):
    za, zb = layer_z(i); y = TPz((za + zb) / 2)
    xa, xb = TPu(Uw) - 34, TPu(-Uw) + 34
    line(xa, y, xa + 20, y, "cut"); line(xb - 20, y, xb, y, "cut")
    line(xa + 20, y, xb - 20, y, "cutthin")
    text(xa - 6, y + 6, ch, "tag", "end")
# z dims (right)
xd = TPu(-Uw) + 62
za, zb = layer_z(0)
dimv(xd, TPz(za), TPz(zb), f"{zb-za:.2f}", ext=[(TPu(-Tm), TPz(za)), (TPu(-Sm + CLR), TPz(zb))])
za1, zb1 = layer_z(1)
dimv(xd, TPz(zb), TPz(za1), f"{ZG:.2f}", ext=[(TPu(-Sm), TPz(za1))], outside=True, tside=1)
dimv(xd + 50, TPz(0), TPz(F), "12.00", ext=[(xd, TPz(0)), (TPu(-Tm), TPz(F))])
# clearance dim at top
zt0, zt1 = layer_z(LAYERS - 1)
dimh(TPu(Sm), TPu(Sm - CLR), TPz(F) - 34, f"{CLR:.2f}",
     ext=[(TPu(Sm), TPz(zt1)), (TPu(Sm - CLR), TPz(zt1))], tpos=TPu(Sm - CLR / 2))
leader(TPu(Sm - CLR / 2), TPz(zt1) - 4, TPu(Uw) - 10, TPz(F) - 64, ["CLOSING", "TRAVEL"], "end")
view_title(fx, 1060, "SECTION F-F", f"DEVELOPED AT R{rm:.2f} (MID-CAP) · 5:1")

# ======== LOAD–DEFLECTION (per wall) ========
gx0, gy0, gw, gh = 560, 990, 330, 300
dmax, fmax = 0.40, 30.0
GX = lambda d: gx0 + gw * d / dmax
GY = lambda f_: gy0 - gh * f_ / fmax
w(f'<rect class="band" x="{GX(0):.2f}" y="{GY(fmax):.2f}" width="{GX(D_PCD_STOP)-GX(0):.2f}" height="{gh}"/>')
for d in (0.1, 0.2, 0.3, 0.4):
    line(GX(d), gy0, GX(d), GY(fmax), "grid")
    text(GX(d), gy0 + 20, f"{d:.2f}", "ts", "middle")
for f_ in (10, 20, 30):
    line(gx0, GY(f_), GX(dmax), GY(f_), "grid")
    text(gx0 - 8, GY(f_) + 4, f"{f_}", "ts", "end")
text(gx0 - 8, gy0 + 4, "0", "ts", "end")
line(gx0, gy0, GX(dmax) + 10, gy0, "axis"); line(gx0, gy0, gx0, GY(fmax) - 10, "axis")
text(GX(dmax), gy0 + 42, "WALL DEFLECTION @ PCD  [mm]", "ts", "end")
text(gx0 - 40, GY(fmax / 2), "LOAD PER WALL  [N]", "ts", "middle", rot=-90)
ds = D_PCD_STOP
poly([(GX(0), GY(0)), (GX(ds), GY(K * ds)), (GX(ds), GY(fmax) + 6)], "curve", False)
line(GX(ds), GY(fmax) + 30, GX(ds), GY(fmax) + 2, "curve", 'marker-end="url(#ahb)"')
w(f'<circle class="op" cx="{GX(PRELOAD):.2f}" cy="{GY(K*PRELOAD):.2f}" r="5.5"/>')
leader(GX(PRELOAD) + 4, GY(K * PRELOAD) + 4, GX(0.15), GY(2.5),
       [f"AT MESH: {K*PRELOAD:.1f} N", "(0.10 PRELOAD)"])
text(GX(ds) + 8, GY(K * ds) + 18, f"FINGERS TOUCH {K*ds:.0f} N", "ts")
text(GX(ds) + 8, GY(26), "RIGID", "tsacc")
text(GX(ds / 2), GY(fmax) + 18, "SPRING", "tsacc", "middle")
text(GX(ds / 2), GY(fmax) + 34, f"k ≈ {K:.0f} N/mm", "ts", "middle")
view_title(gx0 + gw / 2, 1060, "LOAD vs DEFLECTION", "ESTIMATE · SEE NOTE 5")

# ======== NOTES ========
nx, ny = 980, 610
text(nx, ny, "NOTES", "th")
notes = [
    "1. ALL DIMENSIONS IN MM. SOURCE MODEL: compliant_gear.scad.",
    "2. TOOTH IS CUT 0.10 OVERSIZE PER FLANK AT PCD. MESHING AT",
    "    CENTRE DIST. 54.000 PRELOADS BOTH WALLS TOWARD EACH OTHER.",
    "3. BOTH WALLS RUN THE FULL FACE WIDTH. THE TIP IS CLOSED BY",
    f"    {LAYERS} FINGER LAYERS, ALTERNATING L / R, {ZG:.2f} APART IN Z.",
    f"4. FINGERS SLIDE PAST EACH OTHER. A WALL STOPS WHEN ITS FINGER",
    f"    REACHES THE OPPOSITE WALL: {CLR:.2f} CLOSING AT TIP ≈ {D_PCD_STOP:.2f}/WALL @ PCD.",
    f"5. k = 3EI/L³, E 3.5 GPa (RIGID RESIN), L {Lp:.2f}, t {WALL:.2f}, b {F:.2f}.",
    f"    TIP/PCD TRAVEL RATIO {ratio:.2f} (CANTILEVER). FIRST-ORDER; TEST.",
    f"6. FOR SLA / SLS / MJF. {ZG:.2f} LAYER GAP MUST PRINT OPEN.",
]
for i, s in enumerate(notes):
    text(nx, ny + 28 + i * 21, s, "tn")

# ======== TITLE BLOCK ========
bx, by = 980, 900
bx2 = W - 14
w(f'<rect class="tbl" x="{bx}" y="{by}" width="{bx2-bx}" height="{H-14-by}"/>')
line(bx, by + 92, bx2, by + 92, "thin")
line(bx, by + 140, bx2, by + 140, "thin")
for xx in (bx + 150, bx + 300, bx + 450):
    line(xx, by + 92, xx, H - 14, "thin")
text(bx + 14, by + 26, "TITLE", "tk")
text(bx + 14, by + 58, "COMPLIANT ZERO-BACKLASH SPUR GEAR", "ttl")
text(bx + 14, by + 80, "SPLIT-WALL TEETH, INTERLEAVED FINGER CAP", "tv")
cells = [("DWG NO.", "CG-M3-20"), ("REV", "B"), ("SCALE", "AS NOTED"), ("SHEET", "1 / 1"),
         ("MATERIAL", "SLA RESIN"), ("UNITS", "MM"), ("DRAWN", "CLAUDE"), ("DATE", "2026-10-03")]
for i, (k, v) in enumerate(cells):
    col, row = i % 4, i // 4
    x = bx + col * 150 + 10
    y = by + 92 + row * 48
    text(x, y + 16, k, "tk")
    text(x, y + 38, v, "tv")
w('</svg>')

svg = "\n".join(out)
import os
HERE = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(HERE, "template.html")).read().replace("%%SVG%%", svg)
open(os.path.join(HERE, "compliant-gear-drawing.html"), "w").write(html)
print(f"k {K:.1f} wall {WALL:.3f} slot {2*S_HALF:.3f} ratio {ratio:.3f} pcd_stop {D_PCD_STOP:.3f} rm {rm} Tm {Tm:.3f} Sm {Sm:.3f} finger_tip {2*ra*sa(ra)-CLR:.3f}")
