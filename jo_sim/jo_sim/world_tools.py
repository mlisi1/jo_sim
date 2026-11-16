"""World discovery and preprocessing for jo_sim.

* Worlds are looked up by name (``warehouse`` -> ``warehouse.sdf`` / ``warehouse.world``) in, in order:
  the directories in ``$JO_SIM_WORLDS`` (``:``-separated, the host-mounted ``user_worlds/``),
  ``share/jo_sim/worlds`` and the external collection. A path to a file is used as is.
* ``prepare_world`` writes a patched copy of the world that contains the world systems the robot
  needs (missing ones are added) and ``<spherical_coordinates>`` for the GNSS, so any SDF world can be
  dropped in a folder without editing it. Sensor systems the robot model brings itself (IMU, NavSat)
  are not added, otherwise they would run twice.
"""
import os
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory

EXTENSIONS = ('.sdf', '.world')
OUT_DIR = '/tmp/jo_sim/worlds'

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
    d = os.path.dirname(world_path)
    candidates = [d, os.path.join(d, 'models'), os.path.join(os.path.dirname(d), 'models')]
    candidates += search_dirs()
    candidates += [os.path.join(s, 'models') for s in search_dirs()]
    out = []
    for c in candidates:
        c = os.path.abspath(c)
        if os.path.isdir(c) and c not in out:
            out.append(c)
    return out


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

    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, os.path.splitext(os.path.basename(world_path))[0] + '.sdf')
    tree.write(out, encoding='unicode', xml_declaration=True)
    return out, changes
