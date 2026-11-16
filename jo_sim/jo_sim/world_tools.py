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
                c = re.search(r'^\s*diffuse\s+([-\d.]+\s+[-\d.]+\s+[-\d.]+)', block, re.M)
                if c:
                    info['diffuse'] = c.group(1)
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
        if tex is None and 'diffuse' not in info:
            continue
        mat.remove(script)
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


def _convert_models(world, dirs, changes):
    """Ogre material scripts -> PBR, in the world and in the models it uses (converted copies of
    those are written to CONVERTED_MODELS, the other files of the model are linked)."""
    n = _convert_scripts(world, dirs, os.getcwd())
    if n:
        changes.append(f'converted {n} Ogre material scripts in the world')
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
        if '<script>' not in text:
            continue
        try:
            tree = ET.parse(sdf)
        except ET.ParseError:
            continue
        n = _convert_scripts(tree.getroot(), dirs, src, src)
        if not n:
            continue
        os.makedirs(dst, exist_ok=True)
        for entry in os.listdir(src):
            link = os.path.join(dst, entry)
            if entry != 'model.sdf' and not os.path.lexists(link):
                os.symlink(os.path.realpath(os.path.join(src, entry)), link)
        tree.write(os.path.join(dst, 'model.sdf'))
        changes.append(f'model {name}: {n} Ogre material scripts converted to PBR')


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
    _unique_names(world, changes)

    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, os.path.splitext(os.path.basename(world_path))[0] + '.sdf')
    tree.write(out, encoding='unicode', xml_declaration=True)
    return out, changes
