"""The running container of this checkout, for the scripts in docs/gen."""
import functools, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


@functools.lru_cache(maxsize=None)
def container():
    """JO_CONTAINER if set, else this checkout's compose service (the name depends on the folder)."""
    name = os.environ.get('JO_CONTAINER')
    if name:
        return name
    ids = subprocess.run(['docker', 'compose', '--project-directory', str(ROOT), '-f', str(ROOT / 'compose.yaml'),
                          'ps', '-q', '--status', 'running', 'jo-sim'],
                         capture_output=True, text=True).stdout.split()
    if not ids:
        sys.exit(f'[docs/gen] no running container for {ROOT}: run ./jo up first')
    return ids[0]
