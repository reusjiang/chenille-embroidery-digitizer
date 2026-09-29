"""Verify release contents with Python's standard library; no embroidery packages needed."""
from pathlib import Path
import argparse,hashlib,json
from project import ROOT,BASELINE


def verify_release(directory):
    directory=Path(directory).resolve()
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    files=manifest['files']
    if not files or 'Bulldogs_F2_330mm.DST' not in files:
        raise ValueError('Missing required DST in release manifest')
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p.name!='manifest.json'}
    if actual!=set(files):raise ValueError(f'File list differs: {actual.symmetric_difference(files)}')
    for name,expected in files.items():
        path=(directory/name).resolve()
        if not path.is_relative_to(directory):raise ValueError(f'Unsafe manifest path: {name}')
        if not path.is_file():raise ValueError(f'Missing file: {name}')
        if path.stat().st_size!=expected['bytes']:raise ValueError(f'File size differs: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected['sha256']:raise ValueError(f'SHA256 differs: {name}')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',nargs='?',default=str(BASELINE))
    args=parser.parse_args()
    try:m=verify_release(ROOT/args.directory)
    except (OSError,ValueError,KeyError) as e:parser.exit(1,f'FAIL: {e}\n')
    print(f"PASS: {m['release_id']} / {len(m['files'])} files / {m['status']}")
    print('File integrity verified; Wilcom/machine acceptance remains a separate step.')

if __name__=='__main__':main()
