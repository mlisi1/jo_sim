import json, sys, math
import xml.etree.ElementTree as ET
import numpy as np
urdf, meshdir, out = sys.argv[1:4]
root = ET.parse(urdf).getroot()
def tf(origin):
    xyz = [0,0,0]; rpy = [0,0,0]
    if origin is not None:
        xyz = [float(v) for v in origin.get('xyz','0 0 0').split()]
        rpy = [float(v) for v in origin.get('rpy','0 0 0').split()]
    r,p,y = rpy
    Rx = np.array([[1,0,0],[0,math.cos(r),-math.sin(r)],[0,math.sin(r),math.cos(r)]])
    Ry = np.array([[math.cos(p),0,math.sin(p)],[0,1,0],[-math.sin(p),0,math.cos(p)]])
    Rz = np.array([[math.cos(y),-math.sin(y),0],[math.sin(y),math.cos(y),0],[0,0,1]])
    T = np.eye(4); T[:3,:3] = Rz@Ry@Rx; T[:3,3] = xyz; return T
mats = {}
for m in root.findall('material'):
    c = m.find('color')
    if c is not None: mats[m.get('name')] = [float(v) for v in c.get('rgba').split()]
children = {}; parent_of = {}
for j in root.findall('joint'):
    p = j.find('parent').get('link'); c = j.find('child').get('link')
    children.setdefault(p, []).append((c, tf(j.find('origin')))); parent_of[c] = p
links = {l.get('name'): l for l in root.findall('link')}
base = [n for n in links if n not in parent_of][0]
world = {base: np.eye(4)}; stack = [base]
while stack:
    n = stack.pop()
    for c, T in children.get(n, []):
        world[c] = world[n] @ T; stack.append(c)
items = []
for name, l in links.items():
    for v in l.findall('visual'):
        T = world[name] @ tf(v.find('origin'))
        g = v.find('geometry')[0]
        rgba = [0.6,0.6,0.6,1]
        m = v.find('material')
        if m is not None:
            c = m.find('color')
            rgba = [float(x) for x in c.get('rgba').split()] if c is not None else mats.get(m.get('name'), rgba)
        it = {'link': name, 'matrix': T.tolist(), 'rgba': rgba, 'kind': g.tag}
        if g.tag == 'mesh':
            it['file'] = meshdir + '/' + g.get('filename').split('/')[-1]
            it['scale'] = [float(x) for x in g.get('scale','1 1 1').split()]
        elif g.tag == 'box': it['size'] = [float(x) for x in g.get('size').split()]
        elif g.tag == 'cylinder': it['radius'] = float(g.get('radius')); it['length'] = float(g.get('length'))
        elif g.tag == 'sphere': it['radius'] = float(g.get('radius'))
        items.append(it)
json.dump(items, open(out,'w'), indent=1)
from collections import Counter
print('root', base, '| visuals', len(items), Counter(i['kind'] for i in items))
