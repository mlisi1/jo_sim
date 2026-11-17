import bpy, json, sys, math
from mathutils import Matrix, Vector
argv = sys.argv[sys.argv.index('--')+1:]
scene_json, out_png, res = argv[0], argv[1], int(argv[2])
az = float(argv[3]) if len(argv) > 3 else -40.0   # camera azimuth (deg) around z, 0 = in front (+x)
el = float(argv[4]) if len(argv) > 4 else 25.0
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 192
sc.cycles.use_denoising = False
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = res
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'
sc.view_settings.view_transform = 'Standard'
items = json.load(open(scene_json))
matcache = {}
def material(rgba):
    key = tuple(round(c, 3) for c in rgba)
    if key in matcache: return matcache[key]
    m = bpy.data.materials.new(f"m{len(matcache)}"); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgba[:3], 1)
    b.inputs['Roughness'].default_value = 0.45
    b.inputs['Metallic'].default_value = 0.15
    if rgba[3] < 0.99:
        b.inputs['Alpha'].default_value = max(rgba[3], 0.25)
        m.blend_method = 'BLEND'
    matcache[key] = m; return m
objs = []
for it in items:
    before = set(bpy.data.objects)
    try: bpy.ops.wm.stl_import(filepath=it['file'])
    except AttributeError: bpy.ops.import_mesh.stl(filepath=it['file'])
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        o.matrix_world = Matrix(it['matrix']) @ Matrix.Diagonal((*it['scale'], 1))
        o.data.materials.clear(); o.data.materials.append(material(it['rgba']))
        for p in o.data.polygons: p.use_smooth = False
        objs.append(o)
bpy.context.view_layer.update()
pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
center = sum(pts, Vector()) / len(pts)
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
center = (lo + hi) / 2
d = Vector((math.cos(math.radians(el))*math.cos(math.radians(az)), math.cos(math.radians(el))*math.sin(math.radians(az)), math.sin(math.radians(el))))
cam_data = bpy.data.cameras.new('cam'); cam_data.type = 'ORTHO'
cam = bpy.data.objects.new('cam', cam_data); sc.collection.objects.link(cam); sc.camera = cam
cam.location = center + d * 10
cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
bpy.context.view_layer.update()
inv = cam.matrix_world.inverted()
cs = [inv @ p for p in pts]
xs = [c.x for c in cs]; ys = [c.y for c in cs]
cx, cy = (max(xs)+min(xs))/2, (max(ys)+min(ys))/2
cam.location = cam.matrix_world @ Vector((cx, cy, 0))
cam_data.ortho_scale = max(max(xs)-min(xs), max(ys)-min(ys)) * 1.04
# lights: key sun, fill sun, rim; soft world for ambient
def sun(name, rot, energy, color=(1,1,1)):
    l = bpy.data.lights.new(name, 'SUN'); l.energy = energy; l.color = color; l.angle = math.radians(8)
    o = bpy.data.objects.new(name, l); o.rotation_euler = [math.radians(a) for a in rot]; sc.collection.objects.link(o)
sun('key', (40, 0, -60), 4.0)
sun('fill', (60, 0, 120), 1.2, (0.75, 0.9, 1.0))
sun('rim', (110, 0, 160), 2.0, (0.6, 0.9, 1.0))
w = bpy.data.worlds.new('w'); w.use_nodes = True; sc.world = w
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.5, 0.55, 0.62, 1)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
sc.render.filepath = out_png
bpy.ops.render.render(write_still=True)
print('rendered', out_png, 'objects', len(objs))
