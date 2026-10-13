"""Read-only DST inventory; filename hints are never verified design text."""
from collections import Counter, defaultdict
from importlib.metadata import version as package_version
from pathlib import Path
import hashlib
import json
import math
import platform
import re
import string

import pyembroidery as pe


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def project_path(root, value):
    root = Path(root).resolve()
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Path escapes project: {value}')
    return path


def inspect_dst(path):
    """Metadata inspection, not strict validation or a production acceptance gate."""
    raw = path.read_bytes()
    flags = []
    if len(raw) < 515:
        return {'status': 'unreadable', 'flags': ['too_short_for_dst'], 'metrics': None}
    end_offset = next((i for i in range(512, len(raw) - 2, 3)
                       if (raw[i + 2] & 0xF3) == 0xF3), None)
    if end_offset is None:
        flags.append('missing_encoded_end')
    elif raw[end_offset + 3:] not in (b'', b'\x1a'):
        # The historical library writes a single DOS EOF byte after END.
        # Preserve that byte; flag other trailers for inspection only.
        flags.append('unexpected_bytes_after_end')
    try:
        pattern = pe.read_dst(str(path), {'trim_at': False, 'clipping': False})
        rows = pattern.stitches
        if not rows or any(not math.isfinite(v) for row in rows for v in row[:2]):
            raise ValueError('Missing or nonfinite coordinates')
        counts = Counter(int(row[2]) & pe.COMMAND_MASK for row in rows)
        points = [row[:2] for row in rows if (int(row[2]) & pe.COMMAND_MASK) == pe.STITCH]
        width = round((max(p[0] for p in points) - min(p[0] for p in points)) / 10, 1) if points else None
        height = round((max(p[1] for p in points) - min(p[1] for p in points)) / 10, 1) if points else None
        if not points:
            flags.append('no_stitches')
        elif width == 0 or height == 0:
            flags.append('zero_extent_requires_classification')
        return {'status': 'decoded', 'flags': flags,
                'metrics': {'width_mm': width, 'height_mm': height,
                            'stitch_commands': counts[pe.STITCH], 'jump_commands': counts[pe.JUMP],
                            'color_change_commands': counts[pe.COLOR_CHANGE]}}
    except Exception as error:
        return {'status': 'unreadable', 'flags': [*flags, 'decode_failed'],
                'metrics': None, 'error': f'{type(error).__name__}: {error}'}


def inventory(root, config):
    root = Path(root).resolve()
    source = project_path(root, config['source_root'])
    if not source.is_dir():
        raise ValueError(f'Sample library is missing: {source}')
    files = sorted(p for p in source.rglob('*') if p.is_file() and p.suffix.lower() == '.dst')
    if not files:
        raise ValueError('Sample library contains no DST files')
    records = {}
    folders = Counter()
    for path in files:
        if not path.resolve().is_relative_to(source):
            raise ValueError(f'Symlink escapes sample library: {path}')
        folder = path.relative_to(source).parts[0]
        folders[folder] += 1
        font = config['font_directory_map'].get(folder)
        sha = digest(path)
        if sha not in records:
            records[sha] = {
                'sample_id': 'dst-sha256-' + sha, 'sha256': sha,
                'bytes': path.stat().st_size, 'sources': [],
                'reference_use': config['reference_use'],
                'verified_design': None, 'machine_acceptance': None,
                'inspection': inspect_dst(path),
            }
        records[sha]['sources'].append({
            'path': path.relative_to(root).as_posix(), 'font_id_hint': font,
            'font_basis': 'directory_mapping' if font else 'unmapped_directory',
            'text_hint': path.stem, 'text_basis': 'unverified_filename',
            'filename_contains_digit': any(c.isdigit() for c in path.stem),
        })
    return sorted(records.values(), key=lambda record: record['sample_id']), dict(sorted(folders.items()))


def coverage(records, folders, snapshot_id):
    hints = defaultdict(set)
    source_counts = Counter()
    unknown = []
    for record in records:
        for source in record['sources']:
            font = source['font_id_hint']
            if font:
                source_counts[font] += 1
                hints[font].update(c for c in source['text_hint'] if c in string.ascii_letters + string.digits)
            else:
                unknown.append(source['path'])
    return {
        'schema_version': 1, 'snapshot_id': snapshot_id,
        'scope': 'Inventory only. Filename characters do not prove glyph or connection coverage.',
        'source_file_count': sum(folders.values()), 'folder_counts': folders,
        'unique_content_count': len(records),
        'duplicate_content_groups': [
            {'sample_id': r['sample_id'], 'paths': [s['path'] for s in r['sources']]}
            for r in records if len(r['sources']) > 1],
        'flagged_samples': [{'sample_id': r['sample_id'], 'flags': r['inspection']['flags']}
                            for r in records if r['inspection']['flags']],
        'unreadable_samples': [r['sample_id'] for r in records if r['inspection']['status'] != 'decoded'],
        'unmapped_font_paths': unknown,
        'fonts': {font: {
            'source_file_count': source_counts[font],
            'filename_character_hints': ''.join(sorted(hints[font])),
            'verified_characters': [], 'verified_connections': [],
            'verification_status': 'not_annotated',
        } for font in sorted(source_counts)},
    }


def create_snapshot(root, config_path, snapshot_id):
    root = Path(root).resolve()
    if not re.fullmatch(r'v[0-9]{3,}', snapshot_id):
        raise ValueError('Snapshot ID must be v001, v002, ...')
    config_path = project_path(root, config_path)
    config = json.loads(config_path.read_text(encoding='utf-8'))
    output = project_path(root, 'library/catalog/' + snapshot_id)
    report_dir = project_path(root, 'library/coverage/' + snapshot_id)
    if output.exists() or report_dir.exists():
        raise ValueError('Snapshot already exists; choose a new version. Existing records are not overwritten.')
    records, folders = inventory(root, config)
    catalog = {'schema_version': 1, 'snapshot_id': snapshot_id,
               'source_root': config['source_root'], 'samples': records}
    report = coverage(records, folders, snapshot_id)
    catalog_data = json_bytes(catalog)
    report_data = json_bytes(report)
    sources = ['src/chenille/catalog.py', 'src/chenille/__init__.py', 'scripts/index_library.py']
    manifest = {
        'schema_version': 1, 'snapshot_id': snapshot_id,
        'status': 'metadata_indexed_not_design_verified',
        'python': platform.python_version(), 'pyembroidery': package_version('pyembroidery'),
        'config': {'path': config_path.relative_to(root).as_posix(), 'sha256': digest(config_path)},
        'code_sha256': {name: digest(root / name) for name in sources},
        'files': {
            f'library/catalog/{snapshot_id}/catalog.json': hashlib.sha256(catalog_data).hexdigest(),
            f'library/coverage/{snapshot_id}/summary.json': hashlib.sha256(report_data).hexdigest(),
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    report_dir.mkdir(parents=True, exist_ok=False)
    (output / 'catalog.json').write_bytes(catalog_data)
    (report_dir / 'summary.json').write_bytes(report_data)
    (output / 'manifest.json').write_bytes(json_bytes(manifest))
    return report


def verify_snapshot(root, snapshot_id):
    root = Path(root).resolve()
    if not re.fullmatch(r'v[0-9]{3,}', snapshot_id):
        raise ValueError('Invalid snapshot ID')
    manifest = json.loads((root / 'library/catalog' / snapshot_id / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        if digest(project_path(root, name)) != expected:
            raise ValueError(f'Snapshot checksum changed: {name}')
    catalog = json.loads((root / 'library/catalog' / snapshot_id / 'catalog.json').read_text())
    paths = set()
    for record in catalog['samples']:
        if record['sample_id'] != 'dst-sha256-' + record['sha256']:
            raise ValueError('Sample ID does not match content hash')
        for source in record['sources']:
            path = project_path(root, source['path'])
            if digest(path) != record['sha256']:
                raise ValueError(f'Source checksum changed: {source["path"]}')
            paths.add(path)
    source_root = project_path(root, catalog['source_root'])
    actual = {p.resolve() for p in source_root.rglob('*') if p.is_file() and p.suffix.lower() == '.dst'}
    if paths != actual:
        raise ValueError('Library file set changed; build a new snapshot')
    # Historical source hashes are recorded for checkout/reproduction, not required
    # to equal today's code after a later engine upgrade.
    return {'snapshot_id': snapshot_id, 'source_files': len(paths), 'unique_samples': len(catalog['samples'])}
