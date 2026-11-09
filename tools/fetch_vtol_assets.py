"""Fetch the official PX4 standard_vtol assets at one pinned commit."""
from pathlib import Path
import hashlib
import json
import urllib.request

REPO = 'PX4/PX4-gazebo-models'
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'vendor' / 'px4-gazebo-models'


def read(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'INHA-Gazebo-local-setup'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main():
    manifest_path = DEST / 'SOURCE.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        commit = manifest['commit']
    else:
        commit = json.loads(read(f'https://api.github.com/repos/{REPO}/commits/main'))['sha']
    tree = json.loads(read(f'https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1'))
    if tree.get('truncated'):
        raise RuntimeError('GitHub tree was truncated')
    paths = [entry['path'] for entry in tree['tree'] if entry['type'] == 'blob'
             and (entry['path'].startswith('models/standard_vtol/')
                  or entry['path'] == 'LICENSE')]
    records = []
    for relative in paths:
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(read(f'https://raw.githubusercontent.com/{REPO}/{commit}/{relative}'))
        records.append({'path': relative, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                        'bytes': target.stat().st_size})
        print(relative, target.stat().st_size, flush=True)
    manifest = {'repository': f'https://github.com/{REPO}', 'commit': commit,
                'license_file': 'LICENSE', 'files': records}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('Pinned commit:', commit)


if __name__ == '__main__':
    main()
