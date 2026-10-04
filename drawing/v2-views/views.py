"""Standard views (top / front / right / iso + iso detail) of compliant_gear_v2
via OpenCascade hidden-line removal, composed into an SVG drawing sheet."""
import math, sys, time
from build123d import GeomType, Box, Rot, Pos, Align
import model_v2 as M

t0 = time.time()
body = M.build()
print("built", round(time.time() - t0, 1))


def project(shape, eye, look=(0, 0, 0), up=(0, 0, 1)):
    vis, hid = shape.project_to_viewport(eye, up, look)
    return vis, hid


def polylines(edges, tol=0.15):
    out = []
    for e in edges:
        if e.geom_type == GeomType.LINE:
            ps = [e.position_at(0), e.position_at(1)]
        else:
            n = max(4, min(80, int(e.length / tol)))
            ps = [e.position_at(i / n) for i in range(n + 1)]
        out.append([(p.X, p.Y) for p in ps])
    return out


def bbox(pls):
    xs = [x for pl in pls for x, _ in pl]; ys = [y for pl in pls for _, y in pl]
    return min(xs), max(xs), min(ys), max(ys)


VIEWS = {}
D = 400
t = time.time()
VIEWS["top"] = project(body, (0, 0, D), up=(0, 1, 0))
VIEWS["front"] = project(body, (0, -D, M.F / 2), look=(0, 0, M.F / 2))
VIEWS["right"] = project(body, (D, 0, M.F / 2), look=(0, 0, M.F / 2))
VIEWS["iso"] = project(body, (D, -D, D))
print("projected", round(time.time() - t, 1))
# detail: one tooth facing the iso viewer, cropped
ang = -36
crop = Rot(0, 0, ang) * Pos(M.ra - 5.5, 0, M.F / 2) * Box(12, 12, M.F + 2)
tooth = body & crop
VIEWS["detail"] = project(tooth, (D, -D, D))
print("detail", round(time.time() - t, 1))

import json
data = {k: {"vis": polylines(v[0]), "hid": polylines(v[1])} for k, v in VIEWS.items()}
json.dump(data, open("views.json", "w"))
print({k: (len(v["vis"]), len(v["hid"])) for k, v in data.items()})
