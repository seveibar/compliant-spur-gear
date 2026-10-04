# v2 standard views

`compliant-gear-v2-views.html` is a third-angle drawing sheet with top, front, right and isometric views, plus an isometric detail of one tooth.

The views are hidden-line projections (OpenCascade HLR) of an exact B-rep rebuild of `compliant_gear_v2.scad`. The rebuild's volume matches the OpenSCAD STL to 0.04%.

```sh
pip install build123d
python model_v2.py   # builds the B-rep, writes compliant_gear_v2.step
python views.py      # projects the views -> views.json (~1 min)
python sheet.py      # composes the sheet -> compliant-gear-v2-views.html
```

`model_v2.py` copies its parameters from the `.scad` file by hand, so keep the two in sync.
