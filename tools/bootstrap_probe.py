"""検証に使う外部ソースをcommit固定で.cacheへ取得する。"""

import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache'
COMMITS = {
    'ARM9/casfx': 'd0827fb5f4ba8d5fb26b4de3fa1e3a79a6fbc1ed',
    'SourMesen/Mesen2': 'b9fa69ddc6d0a331fb103fdb5eef6904305703c2',
}


def fetch(repo, commit, name, expected_sha):
    dest = CACHE / repo.split('/')[-1] / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or hashlib.sha256(dest.read_bytes()).hexdigest()!=expected_sha:
        url = f'https://raw.githubusercontent.com/{repo}/{commit}/{name}'
        with urllib.request.urlopen(url, timeout=40) as response:
            dest.write_bytes(response.read())
    actual=hashlib.sha256(dest.read_bytes()).hexdigest()
    if actual!=expected_sha:
        raise ValueError(f'hash mismatch: {repo}/{name}')
    return str(dest.relative_to(ROOT)), actual


def main():
    CACHE.mkdir(exist_ok=True)
    manifest_path = CACHE / 'sources.json'
    locked = json.loads((ROOT/'probes/v001/sources.lock.json').read_text())
    manifest = {}
    jobs = []
    sources = {
        'ARM9/casfx': ['gsu/casfx.inc', 'LICENSE', 'gsu/affine.asm', 'header.asm', 'snes_regs.asm'],
        'SourMesen/Mesen2': ['Core/Debugger/LuaApi.cpp', 'Core/SNES/Coprocessors/GSU/Gsu.cpp',
                             'Core/SNES/Coprocessors/GSU/Gsu.Instructions.cpp',
                             'Core/SNES/Coprocessors/GSU/GsuTypes.h',
                             'Core/SNES/SnesConsole.cpp', 'Core/Shared/MemoryType.h'],
    }
    for repo, names in sources.items():
        sha = COMMITS[repo]
        assert locked[repo]['commit']==sha
        if repo not in manifest or manifest[repo]['commit'] != sha:
            manifest[repo] = {'commit': sha, 'files': {}}
        for name in names:
            jobs.append((repo, name, sha, locked[repo]['files'][name]['sha256']))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch, repo, commit, name, expected): (repo, name) for repo, name, commit, expected in jobs}
        for future, (repo, name) in futures.items():
            try:
                path, sha = future.result()
                manifest[repo]['files'][name] = {'path': path, 'sha256': sha}
            except Exception as error:
                raise RuntimeError(f'{repo}/{name}: {error}') from error
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({repo: entry['commit'] for repo, entry in manifest.items()}, indent=2))


if __name__ == '__main__':
    main()
