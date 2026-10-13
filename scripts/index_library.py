#!/usr/bin/env python3
"""Build a versioned index without modifying original DST files."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from chenille.catalog import create_snapshot, verify_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='v001')
    parser.add_argument('--config', default='configs/library-index.json')
    parser.add_argument('--verify', action='store_true', help='Verify snapshot and original file hashes without writing')
    args = parser.parse_args()
    try:
        result = verify_snapshot(ROOT, args.version) if args.verify else create_snapshot(ROOT, args.config, args.version)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'FAIL: {error}\n')
    if args.verify:
        print(f"PASS: {result['source_files']} sources / {result['unique_samples']} unique samples")
    else:
        print(f"Created {args.version}: {result['source_file_count']} sources / {result['unique_content_count']} unique samples")
        print(f"Flagged samples: {len(result['flagged_samples'])}; unreadable: {len(result['unreadable_samples'])}")
    print('Index metadata only; design matching and machine acceptance are separate.')


if __name__ == '__main__':
    main()
