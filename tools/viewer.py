"""Интерактивный 3D-просмотр в браузере: tools/viewer.py → renders/viewer.html (один файл, three.js с CDN).

Запуск: ~/.local/share/uv/tools/build123d-mcp/bin/python tools/viewer.py
Мышь: ЛКМ вращать, ПКМ двигать, колесо зум. Чекбоксы — показать/скрыть детали.
"""
import base64
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from OCP.BRep import BRep_Tool  # noqa: E402
from OCP.BRepMesh import BRepMesh_IncrementalMesh  # noqa: E402
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED  # noqa: E402
from OCP.TopExp import TopExp_Explorer  # noqa: E402
from OCP.TopLoc import TopLoc_Location  # noqa: E402
from OCP.TopoDS import TopoDS  # noqa: E402


def mesh(shape, tol=0.15):
    BRepMesh_IncrementalMesh(shape.wrapped, tol, False, 0.35, True)
    V, I = [], []
    exp = TopExp_Explorer(shape.wrapped, TopAbs_FACE)
    face_of = TopoDS.Face if hasattr(TopoDS, "Face") else TopoDS.Face_s
    while exp.More():
        f = face_of(exp.Current())
        exp.Next()
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f, loc)
        if tri is None:
            continue
        tr = loc.Transformation()
        base = len(V)
        for i in range(1, tri.NbNodes() + 1):
            p = tri.Node(i).Transformed(tr)
            V.append((p.X(), p.Y(), p.Z()))
        rev = f.Orientation() == TopAbs_REVERSED
        for i in range(1, tri.NbTriangles() + 1):
            a, b, c = tri.Triangle(i).Get()
            I.append((base + a - 1, base + c - 1, base + b - 1) if rev else (base + a - 1, base + b - 1, base + c - 1))
    v = np.asarray(V, dtype=np.float32)
    i = np.asarray(I, dtype=np.uint32)
    return base64.b64encode(v.tobytes()).decode(), base64.b64encode(i.tobytes()).decode(), len(I)


def build_objects():
    from build123d import Box, Location, Pos

    import layout as L
    import params as P
    from dummies import screen_plane, screen_step
    from render_layout import C

    CARCASS = {"base", "front_band", "front_screen", "rear", "rail_l", "rail_r"}
    COVER = {"side_l", "side_r", "roof", "roof_block_lf", "roof_block_lb", "roof_block_rf", "roof_block_rb"}
    HW = {"screws", "inserts", "feet"}

    def group_of(name):
        if name in COVER:
            return "Колпак (снимается)", True, 1.0
        if name in CARCASS or name == "screen_bezel":
            return "Каркас", True, 1.0
        if name in HW:
            return "Крепёж", True, 1.0
        if name.endswith("keepout"):
            return "Зоны (keepout)", False, 0.3
        return "Компоненты", True, 1.0
    shapes = {**L.shells, **L.dummies, **L.hardware}
    shapes["crowpanel"] = screen_step()
    shapes["scr_aa"] = Location(screen_plane()) * Pos(0, 0, 0.05) * Box(P.SCR_AA[0], P.SCR_AA[1], 0.1)
    out = []
    for name, col in C.items():
        if name not in shapes:
            continue
        ko = name.endswith("keepout")
        label, vis, op = group_of(name)
        tol = 0.4 if name == "crowpanel" else 0.15
        v, i, n = mesh(shapes[name], tol)
        out.append({"name": name, "group": label, "color": col, "opacity": op, "visible": vis, "v": v, "i": i})
        print(f"{name:22s} {n:7d} tris")
    return out


HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>Таро-ПК — 3D</title>
<style>
html,body{margin:0;height:100%;overflow:hidden;font:13px system-ui,sans-serif;background:#f4f1ea}
#ui{position:absolute;top:10px;left:10px;background:#fffd;padding:10px 12px;border-radius:8px;box-shadow:0 1px 6px #0002;max-height:92vh;overflow:auto}
#ui h3{margin:0 0 6px;font-size:14px} #ui label{display:block;white-space:nowrap} .g{margin-top:8px;font-weight:600}
#ui button{margin:2px 2px 0 0} #hint{position:absolute;bottom:8px;left:10px;color:#666}
</style></head><body><div id="ui"><h3>Таро-ПК</h3>
<div><button data-v="iso">3/4</button><button data-v="front">Спереди</button><button data-v="right">Сбоку</button><button data-v="rear">Сзади</button><button data-v="top">Сверху</button></div>
<label><input type="checkbox" id="explode"> Разнести детали</label>
<label>Разрез X: <input type="range" id="clip" min="-110" max="110" value="110" style="width:140px"></label>
<div id="list"></div></div><div id="hint">ЛКМ — вращать · ПКМ — двигать · колесо — зум</div>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three'; import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const DATA = __DATA__;
const r = new THREE.WebGLRenderer({antialias:true}); r.setPixelRatio(devicePixelRatio); r.setSize(innerWidth,innerHeight);
r.localClippingEnabled = true; document.body.appendChild(r.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0xf4f1ea);
const cam = new THREE.PerspectiveCamera(35, innerWidth/innerHeight, 1, 5000); cam.up.set(0,0,1);
const ctl = new OrbitControls(cam, r.domElement); const target = new THREE.Vector3(0,80,90); ctl.target.copy(target);
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a7f6a, 1.1));
const dl = new THREE.DirectionalLight(0xffffff, 1.4); dl.position.set(-300,-400,500); scene.add(dl);
const dl2 = new THREE.DirectionalLight(0xffffff, 0.5); dl2.position.set(300,400,200); scene.add(dl2);
const grid = new THREE.GridHelper(400, 20, 0xbbb2a0, 0xd8d0c0); grid.rotation.x = Math.PI/2; grid.position.set(0,80,-0.5); scene.add(grid);
const clipPlane = new THREE.Plane(new THREE.Vector3(-1,0,0), 110);
const b64 = (s, T) => { const bin = atob(s); const u = new Uint8Array(bin.length); for (let k=0;k<bin.length;k++) u[k]=bin.charCodeAt(k); return new T(u.buffer); };
const EXPLODE = {roof:[0,0,120], roof_block_lf:[-50,0,95], roof_block_lb:[-50,0,95], roof_block_rf:[50,0,95], roof_block_rb:[50,0,95],
  side_l:[-110,0,40], side_r:[110,0,40], front_screen:[0,-90,40], screen_bezel:[0,-130,60], front_band:[0,-80,0],
  rear:[0,90,0], rail_l:[0,0,70], rail_r:[0,0,70], base:[0,0,-50], feet:[0,0,-50]};
const objs = {}; const groups = {};
for (const o of DATA) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(b64(o.v, Float32Array), 3));
  g.setIndex(new THREE.BufferAttribute(b64(o.i, Uint32Array), 1)); g.computeVertexNormals();
  const m = new THREE.MeshStandardMaterial({color:o.color, roughness:0.75, metalness:0.0, transparent:o.opacity<1,
     opacity:o.opacity, depthWrite:o.opacity>=1, side:THREE.DoubleSide, clippingPlanes:[clipPlane], flatShading:false});
  const mesh = new THREE.Mesh(g, m); mesh.visible = o.visible; mesh.userData = o; scene.add(mesh);
  if (o.opacity>=1 && o.name!=='crowpanel') {
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(g, 30), new THREE.LineBasicMaterial({color:0x333333, transparent:true, opacity:0.35, clippingPlanes:[clipPlane]}));
    mesh.add(e);
  }
  objs[o.name] = mesh; (groups[o.group] ||= []).push(mesh);
}
const list = document.getElementById('list');
for (const [gname, meshes] of Object.entries(groups)) {
  const h = document.createElement('div'); h.className='g';
  const all = document.createElement('input'); all.type='checkbox'; all.checked = meshes.some(m=>m.visible);
  h.append(all, ' '+gname); list.append(h);
  const boxes = [];
  if (meshes.length>1) for (const m of meshes) {
    const l = document.createElement('label'); const c = document.createElement('input'); c.type='checkbox'; c.checked=m.visible;
    c.onchange = () => m.visible = c.checked; boxes.push(c); l.append(c, ' '+m.userData.name); list.append(l);
  }
  all.onchange = () => { for (const m of meshes) m.visible = all.checked; boxes.forEach(b=>b.checked=all.checked); };
}
document.getElementById('explode').onchange = (ev) => { for (const [n,d] of Object.entries(EXPLODE)) if (objs[n]) objs[n].position.set(...(ev.target.checked?d:[0,0,0])); };
document.getElementById('clip').oninput = (ev) => clipPlane.constant = +ev.target.value;
const VIEWS = {iso:[-330,-420,330], front:[0,-620,95], right:[620,80,95], rear:[0,700,95], top:[0,80,700]};
const setView = v => { const p = VIEWS[v]; cam.position.set(p[0], p[1], p[2]); ctl.target.copy(target); ctl.update(); };
document.querySelectorAll('[data-v]').forEach(b => b.onclick = () => setView(b.dataset.v)); setView('iso');
addEventListener('resize', () => { cam.aspect = innerWidth/innerHeight; cam.updateProjectionMatrix(); r.setSize(innerWidth,innerHeight); });
(function loop(){ requestAnimationFrame(loop); ctl.update(); r.render(scene, cam); })();
</script></body></html>"""

if __name__ == "__main__":
    data = build_objects()
    out = os.path.join(ROOT, "renders", "viewer.html")
    with open(out, "w") as fh:
        fh.write(HTML.replace("__DATA__", json.dumps(data)))
    print("->", out, round(os.path.getsize(out) / 1e6, 1), "MB")
