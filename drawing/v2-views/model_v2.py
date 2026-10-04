"""Exact B-rep rebuild of compliant_gear_v2.scad (default parameters) for
hidden-line projections. Parameters mirror the .scad file."""
import math, time
from build123d import (Edge, Wire, Face, Solid, Vector, Box, Cylinder, Rot, Pos,
                       extrude, Compound, Align)

m, N, F, PA, BORE = 3.0, 20, 12.0, 20.0, 8.0
PRELOAD, HF, SLOT_D = 0.10, 0.55, 2.0
CAP_H, CLR, OVH = 1.8, 1.0, 45.0
rp = m * N / 2
rb = rp * math.cos(math.radians(PA))
ra = rp + m
rf = rp - 1.25 * m
rcap = ra - CAP_H
inv = lambda a: math.tan(a) - a


def psi(r, pl=PRELOAD):
    rr = max(r, rb)
    return math.pi / (2 * N) + pl / rp + inv(math.radians(PA)) - inv(math.acos(rb / rr))


sa = lambda r: HF * psi(min(r, ra))
P2 = lambda r, a: Vector(r * math.cos(a), r * math.sin(a), 0)


def rng(a, b, n=24):
    return [a + (b - a) * i / n for i in range(n + 1)]


def tooth_face():
    r0 = rf - 0.6
    rs = rng(r0, ra)
    right = Edge.make_spline([P2(r, -psi(r)) for r in rs])
    left = Edge.make_spline([P2(r, psi(r)) for r in reversed(rs)])
    tip = Edge.make_three_point_arc(P2(ra, -psi(ra)), P2(ra, 0), P2(ra, psi(ra)))
    base = Edge.make_three_point_arc(P2(r0, psi(r0)), P2(r0, 0), P2(r0, -psi(r0)))
    return Face(Wire([right, tip, left, base]))


def slot_face():
    rs = rng(rf, ra + 1)
    pr = [P2(r, -sa(r)) for r in rs]
    pl = [P2(r, sa(r)) for r in reversed(rs)]
    hb = abs(pr[0].Y)
    xb = rf - SLOT_D
    edges = [
        Edge.make_line(Vector(xb, -hb), pr[0]),
        Edge.make_spline(pr),
        Edge.make_line(pr[-1], pl[0]),
        Edge.make_spline(pl),
        Edge.make_line(pl[-1], Vector(xb, hb)),
        Edge.make_three_point_arc(Vector(xb, hb), Vector(xb - hb, 0), Vector(xb, -hb)),
    ]
    return Face(Wire(edges))


def tri(r, side, z):
    aw = side * (sa(r) + 0.01)
    at = -side * (sa(r) - CLR / r)
    h = r * abs(aw - at) / math.tan(math.radians(OVH))
    a = Vector(r * math.cos(at), r * math.sin(at), z)
    lo = Vector(r * math.cos(aw), r * math.sin(aw), z - h)
    hi = Vector(r * math.cos(aw), r * math.sin(aw), z + h)
    return Wire.make_polygon([a, lo, hi], close=True)


def period():
    s_max = rcap * sa(rcap)
    pmin = 2 * (2 * s_max - CLR) / math.tan(math.radians(OVH))
    n = max(1, math.floor(F / pmin))
    return F / n, n


def fingers():
    P, n = period()
    rs = rng(rcap, ra + 0.4, 12)
    wedges = []
    for k in range(-1, n + 1):
        for side, frac in ((1, 0.25), (-1, 0.75)):
            z = (k + frac) * P
            wedges.append(Solid.make_loft([tri(r, side, z) for r in rs]))
    w = wedges[0]
    for x in wedges[1:]:
        w = w + x
    clip = Pos(0, 0, 0) * Cylinder(ra, F, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return w & clip


def build():
    t = time.time()
    disk = Face(Wire([Edge.make_circle(rf)]))
    g2 = disk
    for i in range(N):
        g2 = g2 + Rot(0, 0, i * 360 / N) * tooth_face()
    try:
        corners = [v for v in g2.vertices() if abs(Vector(v).length - rf) < 0.3]
        g2f = g2.fillet_2d(0.6, corners) if hasattr(g2, "fillet_2d") else None
    except Exception as e:  # keep sharp roots if the fillet fails
        print("fillet skipped:", e); g2f = None
    if g2f is not None:
        g2 = g2f
    body = extrude(g2, F)
    body = body - Cylinder(BORE / 2, 3 * F)
    slot = extrude(Pos(0, 0, -1) * slot_face(), F + 2)
    slots = Compound([Rot(0, 0, i * 360 / N) * slot for i in range(N)])
    body = body - slots
    print("body", round(time.time() - t, 1)); t = time.time()
    f1 = fingers()
    fs = Compound([Rot(0, 0, i * 360 / N) * f1 for i in range(N)])
    body = body + fs
    print("fingers", round(time.time() - t, 1))
    return body


if __name__ == "__main__":
    b = build()
    print("valid", b.is_valid, "volume", round(b.volume, 1), "solids", len(b.solids()))
    from build123d import export_step
    export_step(b, "compliant_gear_v2.step")
