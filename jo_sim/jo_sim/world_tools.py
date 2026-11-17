"""World discovery and preprocessing for jo_sim.

* Worlds are looked up by name (``warehouse`` -> ``warehouse.sdf`` / ``warehouse.world``) in, in order:
  the directories in ``$JO_SIM_WORLDS`` (``:``-separated, the host-mounted ``user_worlds/``),
  ``share/jo_sim/worlds`` and the external collection. A path to a file is used as is.
* ``prepare_world`` writes a patched copy of the world, so any SDF world (including Gazebo Classic
  ones) can be dropped in a folder without editing it:
  - adds the world systems the robot needs; sensor systems the robot model brings itself
    (IMU, NavSat) are not added, otherwise they would run twice;
  - adds ``<spherical_coordinates>`` for the GNSS (or replaces the Classic 0,0 placeholder);
  - Classic built-ins ``model://sun`` / ``model://ground_plane`` are written inline;
  - other ``model://`` includes not found locally are downloaded from Gazebo Fuel (OpenRobotics hosts
    the Classic model database, names with spaces) into MODEL_CACHE under their Classic name, with
    their dependencies, or dropped with a warning if unavailable;
  - Ogre material scripts (ignored by Harmonic: untextured models) are converted to PBR texture
    maps, in the world and in converted copies of the models it uses;
  - visual heightmaps are rescaled to the heights Gazebo Classic gave them;
  - Classic (SDF <= 1.6) worlds: <road> drawn as asphalt strips, ambient-only materials get Classic's
    white diffuse;
  - duplicate top-level model names (an error in Harmonic) are made unique.
"""
import io
import json
import os
import re
import shutil
import zipfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory

EXTENSIONS = ('.sdf', '.world')
OUT_DIR = '/tmp/jo_sim/worlds'
FUEL_URL = 'https://fuel.gazebosim.org/1.0/OpenRobotics/models/'
# Fuel models and check_worlds results: in the host-mounted user worlds folder if there is one,
# so they survive the container
CACHE_DIR = os.path.join(os.environ['JO_SIM_WORLDS'], '.cache') if os.environ.get('JO_SIM_WORLDS') \
    else os.path.expanduser('~/.cache/jo_sim')
FUEL_CACHE = os.path.join(CACHE_DIR, 'fuel_models.json')
MODEL_CACHE = os.path.join(CACHE_DIR, 'models')
STATUS_FILE = os.path.join(CACHE_DIR, 'world_status.json')
# Gazebo Classic shipped textures in its media folder (used by heightmaps as file://media/...)
CLASSIC_MEDIA_URL = 'https://raw.githubusercontent.com/gazebosim/gazebo-classic/gazebo11/'
# Copies of models whose Ogre material scripts were converted to PBR (first on the resource path)
CONVERTED_MODELS = os.path.join(CACHE_DIR, 'converted_models')

SUN = '''<light type="directional" name="sun">
  <cast_shadows>true</cast_shadows><pose>0 0 10 0 0 0</pose>
  <diffuse>0.8 0.8 0.8 1</diffuse><specular>0.2 0.2 0.2 1</specular>
  <attenuation><range>1000</range><constant>0.9</constant><linear>0.01</linear><quadratic>0.001</quadratic></attenuation>
  <direction>-0.5 0.1 -0.9</direction>
</light>'''

GROUND_PLANE = '''<model name="ground_plane"><static>true</static>
  <link name="link">
    <collision name="collision"><geometry><plane><normal>0 0 1</normal><size>200 200</size></plane></geometry>
      <surface><friction><ode><mu>100</mu><mu2>50</mu2></ode></friction></surface></collision>
    <visual name="visual"><geometry><plane><normal>0 0 1</normal><size>200 200</size></plane></geometry>
      <material><ambient>0.8 0.8 0.8 1</ambient><diffuse>0.8 0.8 0.8 1</diffuse><specular>0.8 0.8 0.8 1</specular></material></visual>
  </link>
</model>'''

# (canonical filename, plugin name, extra child elements)
REQUIRED_SYSTEMS = [
    ('gz-sim-physics-system', 'gz::sim::systems::Physics', {}),
    ('gz-sim-user-commands-system', 'gz::sim::systems::UserCommands', {}),
    ('gz-sim-scene-broadcaster-system', 'gz::sim::systems::SceneBroadcaster', {}),
    ('gz-sim-sensors-system', 'gz::sim::systems::Sensors', {'render_engine': 'ogre2'}),
    ('RGLServerPluginManager', 'rgl::RGLServerPluginManager', {}),
]


def search_dirs():
    dirs = [d for d in os.environ.get('JO_SIM_WORLDS', '').split(':') if d]
    share = get_package_share_directory('jo_sim')
    dirs += [os.path.join(share, 'worlds'), os.path.join(share, 'worlds', 'external', 'worlds')]
    return [d for d in dirs if os.path.isdir(d)]


def list_worlds():
    """{name: path}; earlier directories win on name clashes."""
    worlds = {}
    for d in search_dirs():
        for root, dirnames, files in os.walk(d):
            # model folders hold model.sdf files, not worlds
            dirnames[:] = sorted(n for n in dirnames if n != 'models')
            if 'model.config' in files:
                continue
            for f in sorted(files):
                name, ext = os.path.splitext(f)
                if ext in EXTENSIONS:
                    worlds.setdefault(name, os.path.join(root, f))
    return worlds


def resolve_world(world):
    if os.path.isfile(world):
        return os.path.abspath(world)
    name = os.path.splitext(os.path.basename(world))[0]
    worlds = list_worlds()
    if name in worlds:
        return worlds[name]
    raise FileNotFoundError(
        f"World '{world}' not found in {search_dirs()}. Available: {', '.join(sorted(worlds))}")


# Spawn pose and GNSS datum used when neither the command line nor the world's sidecar sets them
# (datum: Pisa, UTM 32N; used only for worlds without <spherical_coordinates>)
DEFAULT_SETTINGS = {'x': 0.0, 'y': 0.0, 'z': 0.6, 'yaw': 0.0,
                    'latitude': 43.7167, 'longitude': 10.3966, 'elevation': 0.0}
SPAWN_KEYS = ('x', 'y', 'z', 'yaw')
GNSS_KEYS = ('latitude', 'longitude', 'elevation')


def sidecar_path(world_path):
    """The world's sidecar <name>.yaml: the first search directory that has one (so ./user_worlds
    can override a built-in one, and sidecars for the external collection live in
    jo_sim/worlds), else the file next to the world. None if there is none."""
    name = os.path.splitext(os.path.basename(world_path))[0]
    candidates = [os.path.join(d, name + '.yaml') for d in search_dirs()]
    candidates.append(os.path.splitext(world_path)[0] + '.yaml')
    return next((c for c in candidates if os.path.isfile(c)), None)


def world_settings(world_path, overrides=None, spawn=''):
    """Spawn pose, GNSS datum and description for a world. Priority: `overrides` (command-line
    values; empty strings and None are ignored) > the sidecar > DEFAULT_SETTINGS.

    Sidecar <world>.yaml (all keys optional):
        description: Office with corridors, good for indoor GLIM tests
        spawn: {x: 1.0, y: -2.0, z: 0.6, yaw: 1.57}
        spawns:                      # named alternatives, picked with spawn:=<name>
          dock: {x: 5.0, y: 0.0, yaw: 3.14}
        gnss: {latitude: 43.72, longitude: 10.33, elevation: 48.0}
    """
    import yaml
    path = sidecar_path(world_path)
    side = {}
    if path:
        with open(path) as f:
            side = yaml.safe_load(f) or {}
    settings = dict(DEFAULT_SETTINGS)
    pose = dict(side.get('spawn') or {})
    if spawn:
        named = side.get('spawns') or {}
        if spawn not in named:
            raise ValueError(f"spawn '{spawn}' not in {path or 'the world (no sidecar)'}: "
                             f"available {', '.join(sorted(named)) or 'none'}")
        pose.update(named[spawn])
    settings.update({k: float(v) for k, v in pose.items() if k in SPAWN_KEYS})
    settings.update({k: float(v) for k, v in (side.get('gnss') or {}).items() if k in GNSS_KEYS})
    settings.update({k: float(v) for k, v in (overrides or {}).items()
                     if k in DEFAULT_SETTINGS and v not in (None, '')})
    settings['description'] = side.get('description', '')
    settings['sidecar'] = path
    return settings


def resource_dirs(world_path):
    """Directories to add to GZ_SIM_RESOURCE_PATH for this world (models next to it, etc.)."""
    os.makedirs(CONVERTED_MODELS, exist_ok=True)
    d = os.path.dirname(world_path)
    candidates = [CONVERTED_MODELS, d, os.path.join(d, 'models'), os.path.join(os.path.dirname(d), 'models')]
    candidates += search_dirs()
    candidates += [os.path.join(s, 'models') for s in search_dirs()]
    candidates += [MODEL_CACHE, os.path.join(CACHE_DIR, 'classic')]
    out = []
    for c in candidates:
        c = os.path.abspath(c)
        if os.path.isdir(c) and c not in out:
            out.append(c)
    return out


def local_models(dirs):
    """Names of the models found in the resource directories (folders with a model.config)."""
    names = set()
    for d in dirs + [p for p in os.environ.get('GZ_SIM_RESOURCE_PATH', '').split(':') if p]:
        if os.path.isdir(d):
            for n in os.listdir(d):
                if os.path.isfile(os.path.join(d, n, 'model.config')):
                    names.add(n)
    return names


class FuelIndex:
    """Which Classic model names exist on Fuel; answers cached on disk, network checked once."""

    def __init__(self):
        try:
            with open(FUEL_CACHE) as f:
                self.cache = json.load(f)
        except (OSError, ValueError):
            self.cache = {}
        self.online = None

    @staticmethod
    def url(name):
        return FUEL_URL + urllib.parse.quote(name.replace('_', ' '))

    def _exists(self, name):
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url(name)), timeout=4) as r:
                return r.status == 200
        except urllib.error.HTTPError:
            return False

    def lookup(self, name):
        if name in self.cache:
            return self.cache[name]
        if self.online is False:
            return False
        try:
            found = self._exists(name)
            self.online = True
        except OSError:
            self.online = False
            return False
        self.cache[name] = found
        return found

    def fetch(self, name, local):
        """Download a Classic model from Fuel into MODEL_CACHE/<name>, with its model:// dependencies.

        Fuel stores the Classic models as e.g. "construction barrel", but their files still refer to
        themselves as model://construction_barrel/...: kept under the Classic name they resolve locally.
        """
        target = os.path.join(MODEL_CACHE, name)
        if os.path.isfile(os.path.join(target, 'model.config')):
            return True
        if not self.lookup(name):
            return False
        url = self.url(name) + '/tip/' + urllib.parse.quote(name.replace('_', ' ').lower()) + '.zip'
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = r.read()
            tmp = target + '.part'
            shutil.rmtree(tmp, ignore_errors=True)
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for m in z.namelist():
                    dest = os.path.realpath(os.path.join(tmp, m))
                    if not dest.startswith(os.path.realpath(tmp) + os.sep):
                        raise ValueError(f'unsafe path in {url}: {m}')
                z.extractall(tmp)
            os.replace(tmp, target)
        except (OSError, ValueError, zipfile.BadZipFile):
            shutil.rmtree(target + '.part', ignore_errors=True)
            return False
        local.add(name)
        # Some Fuel models refer to themselves by their display name (model://Pine Tree/...)
        try:
            display = ET.parse(os.path.join(target, 'model.config')).getroot().findtext('name', '').strip()
            link = os.path.join(MODEL_CACHE, display)
            if display and display != name and '/' not in display and not os.path.lexists(link):
                os.symlink(name, link)
        except (OSError, ET.ParseError):
            pass
        for root, _, files in os.walk(target):
            for f in files:
                if f.endswith(('.sdf', '.material', '.config')):
                    with open(os.path.join(root, f), errors='replace') as fh:
                        deps = set(re.findall(r'model://([A-Za-z0-9_\-]+)', fh.read()))
                    for dep in deps - local - {'sun', 'ground_plane'}:
                        self.fetch(dep, local)
        return True

    def save(self):
        os.makedirs(os.path.dirname(FUEL_CACHE), exist_ok=True)
        with open(FUEL_CACHE, 'w') as f:
            json.dump(self.cache, f, indent=1, sort_keys=True)


def _fix_includes(world, local, changes):
    fuel = FuelIndex()
    for inc in list(world.findall('include')):
        uri = inc.find('uri')
        if uri is None or not (uri.text or '').strip().startswith('model://'):
            continue
        name = uri.text.strip()[len('model://'):].strip('/').split('/')[0]
        if name in local:
            continue
        if name in ('sun', 'ground_plane'):
            elem = ET.fromstring(SUN if name == 'sun' else GROUND_PLANE)
            pose = inc.find('pose')
            if name == 'ground_plane' and pose is not None:
                elem.insert(0, pose)
            if inc.find('name') is not None and name == 'ground_plane':
                elem.set('name', inc.find('name').text)
            world.insert(list(world).index(inc), elem)
            world.remove(inc)
            changes.append(f'inlined Classic built-in {name}')
        elif fuel.fetch(name, local):
            changes.append(f'model {name}: downloaded from Gazebo Fuel')
        else:
            world.remove(inc)
            changes.append(f'WARNING model {name} not found locally nor on Fuel: removed')
    # model:// resources used by inline models (meshes, materials)
    for uri in world.iter('uri'):
        m = re.match(r'\s*model://([^/<\s]+)', uri.text or '')
        if m and m.group(1) not in local:
            name = m.group(1)
            if fuel.fetch(name, local):
                changes.append(f'model {name}: downloaded from Gazebo Fuel')
            else:
                local.add(name)  # report once
                changes.append(f'WARNING resource model://{name} not found locally nor on Fuel')
    fuel.save()


def _fetch_classic_media(world, dirs, changes):
    """file://media/... (textures of the Gazebo Classic install, used by heightmaps): download them from
    the gazebo-classic repo into CACHE_DIR/classic, which is on the resource path (sdformat resolves
    file://media/x against it). References are searched in the world and in the models it includes."""
    texts = [ET.tostring(world, encoding='unicode')]
    for uri in world.iter('uri'):
        m = re.match(r'\s*model://([^/<\s]+)', uri.text or '')
        for d in dirs if m else []:
            sdf = os.path.join(d, m.group(1), 'model.sdf')
            if os.path.isfile(sdf):
                with open(sdf, errors='replace') as f:
                    texts.append(f.read())
                break
    refs = set()
    for t in texts:
        refs.update(re.findall(r'file://(media/[^<\s"]+\.(?:png|jpg|jpeg|dds|tga))', t))
    for rel in sorted(refs):
        local = os.path.join(CACHE_DIR, 'classic', rel)
        if os.path.isfile(local):
            continue
        try:
            with urllib.request.urlopen(CLASSIC_MEDIA_URL + rel, timeout=30) as r:
                data = r.read()
            os.makedirs(os.path.dirname(local), exist_ok=True)
            with open(local, 'wb') as f:
                f.write(data)
            changes.append(f'Classic texture {os.path.basename(rel)}: downloaded')
        except OSError:
            changes.append(f'WARNING Classic texture {rel} not available')


def _resolve_uri(uri, dirs, base):
    """model://X/sub, file://path or relative path -> local path (or None)."""
    uri = (uri or '').strip()
    if uri.startswith('model://'):
        rest = uri[len('model://'):]
        name, _, sub = rest.partition('/')
        for d in dirs:
            if d != CONVERTED_MODELS and os.path.isdir(os.path.join(d, name)):
                return os.path.join(d, name, sub)
        return None
    if uri.startswith('file://'):
        uri = uri[len('file://'):]
    path = uri if os.path.isabs(uri) else os.path.join(base, uri)
    return path if os.path.exists(path) else None


def _ogre_materials(script_dirs):
    """Parse the .material files: name -> {'texture': file, 'normal': file, 'diffuse': 'r g b'}."""
    out = {}
    for d in script_dirs:
        files = [d] if os.path.isfile(d) else [
            os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if f.endswith('.material')]
        for path in files:
            with open(path, errors='replace') as f:
                text = re.sub(r'//[^\n]*', '', f.read())
            for m in re.finditer(r'^\s*material\s+(\S+)[^{]*\{', text, re.M):
                depth, i = 1, m.end()
                while depth and i < len(text):
                    depth += {'{': 1, '}': -1}.get(text[i], 0)
                    i += 1
                block = text[m.end():i]
                info = {}
                t = re.search(r'^\s*texture\s+(\S+)', block, re.M)
                if t:
                    info['texture'] = t.group(1)
                n = re.search(r'normal_map\s+(\S+)', block)
                if n:
                    info['normal'] = n.group(1)
                c = re.search(r'^\s*diffuse\s+([-\d.]+\s+[-\d.]+\s+[-\d.]+)(\s+[-\d.]+)?', block, re.M)
                if c:
                    info['diffuse'] = c.group(1)
                    if c.group(2):
                        info['alpha'] = float(c.group(2))
                if re.search(r'scene_blend\s+alpha_blend', block):
                    info['blend'] = True
                out.setdefault(m.group(1), info)
    return out


def _find_file(name, search):
    for d in search:
        if os.path.isfile(d):
            d = os.path.dirname(d)
        for root, _, files in os.walk(d):
            if name in files:
                return os.path.join(root, name)
    return None


def _convert_scripts(root, dirs, base, model_dir=None):
    """Replace <material><script> (Ogre, ignored by Harmonic) with PBR maps. Returns the count."""
    count = 0
    for mat in root.iter('material'):
        script = mat.find('script')
        if script is None:
            continue
        name = (script.findtext('name') or '').strip()
        if name.startswith('Gazebo/'):
            continue  # built-in Classic colours: Harmonic maps them itself
        locs = [p for p in (_resolve_uri(u.text, dirs, base) for u in script.findall('uri')) if p]
        info = _ogre_materials(locs).get(name)
        if info is None:
            continue
        search = locs + ([model_dir] if model_dir else [])
        tex = _find_file(info['texture'], search) if 'texture' in info else None
        if tex is None and 'diffuse' not in info and not info.get('blend'):
            continue
        mat.remove(script)
        if info.get('blend'):
            # Classic alpha-blended material (water, glass): keep it see-through. A shader-only one
            # (e.g. ocean waves) has no colour: use a water blue.
            visual = next((v for v in root.iter('visual') if mat in list(v)), None)
            if visual is not None and visual.find('transparency') is None:
                ET.SubElement(visual, 'transparency').text = f"{1.0 - info.get('alpha', 0.4):g}"
            if tex is None and 'diffuse' not in info:
                info['diffuse'] = '0.2 0.45 0.6'
        if tex:
            for tag in ('ambient', 'diffuse'):
                if mat.find(tag) is None:
                    ET.SubElement(mat, tag).text = '1 1 1 1'
            metal = ET.SubElement(ET.SubElement(mat, 'pbr'), 'metal')
            ET.SubElement(metal, 'albedo_map').text = tex
            normal = _find_file(info['normal'], search) if 'normal' in info else None
            if normal:
                ET.SubElement(metal, 'normal_map').text = normal
        else:
            for tag in ('ambient', 'diffuse'):
                if mat.find(tag) is None:
                    ET.SubElement(mat, tag).text = info['diffuse'] + ' 1'
        count += 1
    return count


def _image_max(path):
    """Brightest value of a heightmap image and the format maximum (255 / 65535), or None."""
    try:
        from PIL import Image
        import numpy as np
        img = Image.open(path)
        a = np.asarray(img.convert('I') if img.mode in ('I;16', 'I') else img.convert('L'))
        return float(a.max()), 65535.0 if img.mode in ('I;16', 'I') else 255.0
    except Exception:  # PIL missing, unreadable image, ...
        return None


def _fix_heightmaps(root, dirs, base):
    """Visual heightmaps at the heights Gazebo Classic gave them. Classic: z = pixel / 255 * size.z
    + pos.z; Harmonic's renderer: z = pixel / brightest pixel * size.z + pos.z (measured on
    small_city, terrain 2.5 m above the streets). size.z is rescaled by brightest / 255.
    Collision heightmaps are not touched."""
    count = 0
    for link in root.iter('link'):
        for vis in link.findall('visual'):
            hm = vis.find('geometry/heightmap')
            if hm is None:
                continue
            path = _resolve_uri(hm.findtext('uri'), dirs, base)
            m = _image_max(path) if path else None
            size = (hm.findtext('size') or '1 1 1').split()
            if m is None or m[0] <= 0 or len(size) < 3:
                continue
            size[2] = f'{float(size[2]) * m[0] / m[1]:g}'
            hm.find('size').text = ' '.join(size)
            count += 1
    return count


def _convert_models(world, dirs, changes):
    """Ogre material scripts -> PBR, in the world and in the models it uses (converted copies of
    those are written to CONVERTED_MODELS, the other files of the model are linked)."""
    n = _convert_scripts(world, dirs, os.getcwd())
    if n:
        changes.append(f'converted {n} Ogre material scripts in the world')
    n = _fix_heightmaps(world, dirs, os.getcwd())
    if n:
        changes.append(f'{n} heightmaps in the world adjusted to Classic heights')
    todo = {m.group(1) for u in world.iter('uri')
            for m in [re.match(r'\s*model://([^/<\s]+)', u.text or '')] if m}
    done = set()
    while todo:
        name = todo.pop()
        done.add(name)
        src = next((os.path.join(d, name) for d in dirs
                    if d != CONVERTED_MODELS and os.path.isfile(os.path.join(d, name, 'model.sdf'))), None)
        if src is None:
            continue
        sdf = os.path.join(src, 'model.sdf')
        with open(sdf, errors='replace') as f:
            text = f.read()
        todo |= set(re.findall(r'model://([A-Za-z0-9_\- ]+)', text)) - done
        dst = os.path.join(CONVERTED_MODELS, name)
        if '<script>' not in text and '<heightmap>' not in text:
            continue
        try:
            tree = ET.parse(sdf)
        except ET.ParseError:
            continue
        n = _convert_scripts(tree.getroot(), dirs, src, src)
        h = _fix_heightmaps(tree.getroot(), dirs, src)
        if not n and not h:
            continue
        os.makedirs(dst, exist_ok=True)
        for entry in os.listdir(src):
            link = os.path.join(dst, entry)
            if entry != 'model.sdf' and not os.path.lexists(link):
                os.symlink(os.path.realpath(os.path.join(src, entry)), link)
        tree.write(os.path.join(dst, 'model.sdf'))
        if n:
            changes.append(f'model {name}: {n} Ogre material scripts converted to PBR')
        if h:
            changes.append(f'model {name}: {h} heightmaps adjusted to Classic heights')


def _convert_roads(world, changes):
    """Classic <road> (not drawn by Harmonic) -> a static model with one flat asphalt strip per
    segment, visual only like in Classic."""
    import math
    roads = world.findall('road')
    for road in roads:
        width = float(road.findtext('width') or 1.0)
        pts = [[float(v) for v in p.text.split()] for p in road.findall('point') if p.text]
        model = ET.Element('model', name=road.get('name', 'road'))
        ET.SubElement(model, 'static').text = 'true'
        link = ET.SubElement(model, 'link', name='link')
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            a, b = (a + [0.0])[:3], (b + [0.0])[:3]
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if length < 1e-6:
                continue
            vis = ET.SubElement(link, 'visual', name=f'segment_{i}')
            # extend by half the width so consecutive segments overlap at the corners
            ET.SubElement(vis, 'pose').text = (f'{(a[0] + b[0]) / 2} {(a[1] + b[1]) / 2} '
                                               f'{(a[2] + b[2]) / 2} 0 0 {math.atan2(dy, dx)}')
            # top 5 cm above the road points: Classic drew roads over coplanar terrain, Harmonic
            # would hide them under a heightmap at the same height
            ET.SubElement(ET.SubElement(ET.SubElement(vis, 'geometry'), 'box'), 'size').text = \
                f'{length + width} {width} 0.1'
            mat = ET.SubElement(vis, 'material')
            ET.SubElement(mat, 'ambient').text = '0.25 0.25 0.25 1'
            ET.SubElement(mat, 'diffuse').text = '0.25 0.25 0.25 1'
        world.insert(list(world).index(road), model)
        world.remove(road)
    if roads:
        changes.append(f'{len(roads)} Classic <road> elements drawn as asphalt strips')


def _classic_default_diffuse(world, changes):
    """Classic kept the Ogre default (white) diffuse when a material gave only <ambient>; Harmonic
    uses the SDF default (black): such visuals turned black (e.g. small_city sidewalks)."""
    n = 0
    for mat in world.iter('material'):
        if mat.find('ambient') is not None and mat.find('diffuse') is None \
                and mat.find('script') is None and mat.find('pbr') is None:
            ET.SubElement(mat, 'diffuse').text = '1 1 1 1'
            n += 1
    if n:
        changes.append(f'{n} ambient-only materials given the Classic white diffuse')


# The fastest robot sensor is the Xsens IMU at 200 Hz: Gazebo publishes a sensor at most once per
# physics step, so a coarser step lowers its rate (many Classic worlds use 10 ms: IMU at 100 Hz).
MAX_STEP_SIZE = 0.005


def _cap_step_size(world, changes):
    """Cap <physics><max_step_size> so every sensor keeps the robot's rate; real_time_update_rate
    is scaled with it so the target real-time factor does not change."""
    for physics in world.findall('physics'):
        step = physics.find('max_step_size')
        try:
            value = float(step.text)
        except (AttributeError, TypeError, ValueError):
            continue  # Harmonic default (1 ms)
        if value <= MAX_STEP_SIZE:
            continue
        step.text = str(MAX_STEP_SIZE)
        rate = physics.find('real_time_update_rate')
        try:
            if rate is not None and float(rate.text) > 0:
                rate.text = str(float(rate.text) * value / MAX_STEP_SIZE)
        except (TypeError, ValueError):
            pass
        changes.append(f'physics step {value * 1000:g} ms -> {MAX_STEP_SIZE * 1000:g} ms '
                       '(sensors publish at most once per step: IMU at 200 Hz)')


def _unique_names(world, changes):
    seen = {}
    for elem in world:
        if elem.tag == 'model':
            holder, key = elem, None
        elif elem.tag == 'include' and elem.find('name') is not None:
            holder, key = elem.find('name'), 'text'
        else:
            continue
        name = holder.get('name') if key is None else holder.text
        if not name:
            continue
        if name in seen:
            seen[name] += 1
            new = f'{name}_{seen[name]}'
            if key is None:
                holder.set('name', new)
            else:
                holder.text = new
            changes.append(f'renamed duplicate model {name} -> {new}')
        else:
            seen[name] = 1


def _canonical(filename):
    f = os.path.basename(filename)
    if f.startswith('lib'):
        f = f[3:]
    if f.endswith('.so'):
        f = f[:-3]
    return f.replace('ignition-gazebo-', 'gz-sim-').replace('gz-sim8-', 'gz-sim-')


def _is_placeholder_datum(sc):
    def val(tag):
        e = sc.find(tag)
        try:
            return float(e.text) if e is not None and e.text else 0.0
        except ValueError:
            return 0.0
    return val('latitude_deg') == 0.0 and val('longitude_deg') == 0.0


def prepare_world(world_path, latitude, longitude, elevation=0.0, out_dir=OUT_DIR):
    """Write a patched copy of the world and return (path, list of changes)."""
    tree = ET.parse(world_path)
    root = tree.getroot()
    world = root.find('world')
    if world is None:
        raise ValueError(f'{world_path}: no <world> element')

    changes = []
    present = {_canonical(p.get('filename', '')) for p in world.findall('plugin')}
    for filename, name, children in REQUIRED_SYSTEMS:
        if filename in present:
            continue
        plugin = ET.Element('plugin', {'filename': filename, 'name': name})
        for tag, text in children.items():
            ET.SubElement(plugin, tag).text = text
        world.insert(0, plugin)
        changes.append(f'added system {name}')

    sc = world.find('spherical_coordinates')
    if sc is not None and _is_placeholder_datum(sc):
        # Gazebo Classic worlds ship a 0,0 placeholder: use the configured datum instead
        world.remove(sc)
        sc = None
        changes.append('replaced placeholder spherical_coordinates (0, 0)')
    if sc is None:
        sc = ET.SubElement(world, 'spherical_coordinates')
        for tag, text in (('surface_model', 'EARTH_WGS84'), ('world_frame_orientation', 'ENU'),
                          ('latitude_deg', str(latitude)), ('longitude_deg', str(longitude)),
                          ('elevation', str(elevation)), ('heading_deg', '0')):
            ET.SubElement(sc, tag).text = text
        changes.append(f'added spherical_coordinates ({latitude}, {longitude})')

    for speed in world.findall('scene/sky/clouds/speed'):
        if speed.text and speed.text.strip().startswith('-'):
            speed.text = speed.text.strip()[1:]
            changes.append('cloud speed made positive (Classic allowed negative values)')

    _fix_includes(world, local_models(resource_dirs(world_path)), changes)
    _fetch_classic_media(world, resource_dirs(world_path), changes)
    _convert_models(world, resource_dirs(world_path), changes)
    if tuple(int(v) for v in re.findall(r'\d+', root.get('version', '1.9'))[:2]) <= (1, 6):
        _convert_roads(world, changes)
        _classic_default_diffuse(world, changes)
    _unique_names(world, changes)
    _cap_step_size(world, changes)

    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, os.path.splitext(os.path.basename(world_path))[0] + '.sdf')
    tree.write(out, encoding='unicode', xml_declaration=True)
    return out, changes
