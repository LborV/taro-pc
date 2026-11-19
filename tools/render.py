"""Ортографические/перспективные рендеры сборки через VTK (offscreen).

Запуск интерпретатором build123d-mcp (там есть vtk):
    ~/.local/share/uv/tools/build123d-mcp/bin/python tools/render.py layout
Сцены описаны в SCENES ниже; каждая сцена = набор объектов (name -> shape, цвет, прозрачность)
и список видов.
"""
import os
import sys

import vtk

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)


FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _font(tp):
    tp.SetFontFamily(vtk.VTK_FONT_FILE)
    tp.SetFontFile(FONT)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def to_polydata(shape, tol=0.2):
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS
    BRepMesh_IncrementalMesh(shape.wrapped, tol, False, 0.3, True)
    pts = vtk.vtkPoints()
    cells = vtk.vtkCellArray()
    exp = TopExp_Explorer(shape.wrapped, TopAbs_FACE)
    while exp.More():
        f = TopoDS.Face(exp.Current()) if hasattr(TopoDS, "Face") else TopoDS.Face_s(exp.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f, loc)
        exp.Next()
        if tri is None:
            continue
        trsf = loc.Transformation()
        base = pts.GetNumberOfPoints()
        for i in range(1, tri.NbNodes() + 1):
            p = tri.Node(i).Transformed(trsf)
            pts.InsertNextPoint(p.X(), p.Y(), p.Z())
        rev = f.Orientation() == TopAbs_REVERSED
        for i in range(1, tri.NbTriangles() + 1):
            a, b, c = tri.Triangle(i).Get()
            if rev:
                b, c = c, b
            cells.InsertNextCell(3)
            for k in (a, b, c):
                cells.InsertCellPoint(base + k - 1)
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(cells)
    n = vtk.vtkPolyDataNormals()
    n.SetInputData(pd)
    n.SetFeatureAngle(35)
    n.SplittingOn()
    n.ConsistencyOn()
    n.AutoOrientNormalsOn()
    n.Update()
    return n.GetOutput()


def clip(pd, axis, at, keep_below=True):
    plane = vtk.vtkPlane()
    o = [0, 0, 0]
    o["xyz".index(axis)] = at
    nrm = [0, 0, 0]
    nrm["xyz".index(axis)] = -1 if keep_below else 1
    plane.SetOrigin(*o)
    plane.SetNormal(*nrm)
    c = vtk.vtkClipPolyData()
    c.SetInputData(pd)
    c.SetClipFunction(plane)
    c.Update()
    return c.GetOutput()


VIEWS = {
    #  name: (direction from target to camera, view-up)
    "front": ((0, -1, 0), (0, 0, 1)),
    "rear": ((0, 1, 0), (0, 0, 1)),
    "right": ((1, 0, 0), (0, 0, 1)),
    "left": ((-1, 0, 0), (0, 0, 1)),
    "top": ((0, 0, 1), (0, 1, 0)),
    "bottom": ((0, 0, -1), (0, -1, 0)),
    "iso_front": ((-0.8, -1.3, 0.9), (0, 0, 1)),
    "iso_front_r": ((0.9, -1.3, 0.8), (0, 0, 1)),
    "iso_rear": ((0.9, 1.3, 1.0), (0, 0, 1)),
    "iso_top": ((-0.5, -0.7, 1.6), (0, 0, 1)),
}


def render(objs, view, out, size=(1400, 1050), clip_spec=None, title="", ortho=None, edges=True, legend=None,
           labels=None, zoom=1.0, cam_dir=None, lines=None, extra_bounds=None):
    """objs: list of (name, shape, hex color, opacity)."""
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    ren.SetUseDepthPeeling(True)
    ren.SetMaximumNumberOfPeels(8)
    for name, shape, col, op in objs:
        pd = to_polydata(shape)
        if clip_spec:
            pd = clip(pd, *clip_spec)
        m = vtk.vtkPolyDataMapper()
        m.SetInputData(pd)
        a = vtk.vtkActor()
        a.SetMapper(m)
        p = a.GetProperty()
        p.SetColor(*hex2rgb(col))
        p.SetOpacity(op)
        p.SetAmbient(0.35)
        p.SetDiffuse(0.7)
        p.SetSpecular(0.08)
        ren.AddActor(a)
        if edges and op > 0.6:
            fe = vtk.vtkFeatureEdges()
            fe.SetInputData(pd)
            fe.BoundaryEdgesOn()
            fe.FeatureEdgesOn()
            fe.SetFeatureAngle(35)
            fe.ManifoldEdgesOff()
            fe.NonManifoldEdgesOff()
            em = vtk.vtkPolyDataMapper()
            em.SetInputConnection(fe.GetOutputPort())
            em.ScalarVisibilityOff()
            ea = vtk.vtkActor()
            ea.SetMapper(em)
            ea.GetProperty().SetColor(0.15, 0.15, 0.15)
            ea.GetProperty().SetLineWidth(1.2)
            ren.AddActor(ea)
    if extra_bounds:   # невидимые точки, чтобы камера захватила линии
        for p0 in extra_bounds:
            sp = vtk.vtkSphereSource()
            sp.SetCenter(*p0)
            sp.SetRadius(0.01)
            m = vtk.vtkPolyDataMapper()
            m.SetInputConnection(sp.GetOutputPort())
            a = vtk.vtkActor()
            a.SetMapper(m)
            a.GetProperty().SetOpacity(0.0)
            ren.AddActor(a)
    d, up = VIEWS[view] if cam_dir is None else cam_dir
    cam = ren.GetActiveCamera()
    ren.ResetCamera()
    fp = cam.GetFocalPoint()
    dist = 1000
    import math
    L = math.sqrt(sum(c * c for c in d))
    cam.SetPosition(*(fp[i] + d[i] / L * dist for i in range(3)))
    cam.SetViewUp(*up)
    if ortho is None:
        ortho = not view.startswith("iso")
    cam.SetParallelProjection(ortho)
    ren.ResetCamera()
    if ortho:
        cam.SetParallelScale(cam.GetParallelScale() * 0.9 / zoom)
    else:
        cam.Zoom(0.95 * zoom)
    light = vtk.vtkLight()
    light.SetLightTypeToCameraLight()
    light.SetPosition(0.4, 0.6, 1)
    ren.AddLight(light)
    if title:
        t = vtk.vtkTextActor()
        t.SetInput(title)
        _font(t.GetTextProperty())
        t.GetTextProperty().SetFontSize(26)
        t.GetTextProperty().SetColor(0.1, 0.1, 0.1)
        t.SetPosition(20, size[1] - 50)
        ren.AddViewProp(t)
    if legend:
        y = 20
        for label, col in reversed(legend):
            t = vtk.vtkTextActor()
            t.SetInput("■ " + label)
            tp = t.GetTextProperty()
            tp.SetFontSize(17)
            tp.SetColor(*hex2rgb(col))
            _font(tp)
            t.SetPosition(20, y)
            ren.AddViewProp(t)
            y += 22
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetSize(*size)
    rw.SetMultiSamples(8)
    rw.AddRenderer(ren)
    rw.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.Update()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(out)
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()
    if labels or lines:
        _draw_labels(ren, out, labels or [], size, lines or [])
    print("render ->", os.path.relpath(out, ROOT))


def _to_px(ren, p, H):
    c = vtk.vtkCoordinate()
    c.SetCoordinateSystemToWorld()
    c.SetValue(*p)
    x, y = c.GetComputedDisplayValue(ren)
    return x, H - y


def _draw_labels(ren, out, labels, size, lines=()):
    """labels: [(text, (x, y, z)), ...] или (text, xyz, (dx, dy)) — выноски с линиями (PIL)."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(out).convert("RGB")
    dr = ImageDraw.Draw(img)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    W, H = size
    fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    for ln in lines:
        p0, p1, col = ln[0], ln[1], ln[2]
        a, b = _to_px(ren, p0, H), _to_px(ren, p1, H)
        dr.line([a, b], fill=col, width=ln[3] if len(ln) > 3 else 3)
        if len(ln) > 4 and ln[4]:
            dr.text((b[0] + 8, b[1] - 12), ln[4], font=fs, fill=col)
    for lab in labels:
        text, p = lab[0], lab[1]
        c = vtk.vtkCoordinate()
        c.SetCoordinateSystemToWorld()
        c.SetValue(*p)
        x, y = c.GetComputedDisplayValue(ren)
        y = H - y
        if len(lab) > 2 and lab[2] is not None:
            dx, dy = lab[2]
        else:
            vx, vy = x - W / 2, y - H / 2
            n = max((vx * vx + vy * vy) ** 0.5, 1)
            dx, dy = 90 * vx / n, 90 * vy / n
        bx, by = x + dx, y + dy
        dr.line([(x, y), (bx, by)], fill=(200, 30, 30), width=3)
        dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(200, 30, 30))
        tw = dr.textlength(text, font=f)
        r = max(22, tw / 2 + 12)
        if len(text) <= 2:
            dr.ellipse([bx - r, by - 22, bx + r, by + 22], fill=(255, 255, 255), outline=(200, 30, 30), width=3)
        else:
            dr.rounded_rectangle([bx - r, by - 22, bx + r, by + 22], 10, fill=(255, 255, 255),
                                 outline=(200, 30, 30), width=3)
        dr.text((bx - tw / 2, by - 15), text, font=f, fill=(150, 20, 20))
    img.save(out)
