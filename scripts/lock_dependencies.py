"""Resolve only runtime dependency closure, excluding unrelated local tools."""
from importlib.metadata import distribution
from packaging.requirements import Requirement
from pathlib import Path

seen = {}
def visit(name):
    dist = distribution(name)
    canonical = dist.metadata['Name'].lower().replace('_', '-')
    if canonical in seen:
        return
    seen[canonical] = f"{dist.metadata['Name']}=={dist.version}"
    for raw in dist.requires or []:
        req = Requirement(raw)
        if req.marker is None or req.marker.evaluate({'extra': ''}):
            visit(req.name)

for line in Path('requirements.txt').read_text().splitlines():
    if line and not line.startswith('#'):
        visit(Requirement(line).name)
Path('requirements-lock.txt').write_text('# Runtime dependency lock resolved on Python 3.13, Windows.\n' + '\n'.join(sorted(seen.values(), key=str.lower)) + '\n')
print(f'Locked {len(seen)} runtime packages.')
