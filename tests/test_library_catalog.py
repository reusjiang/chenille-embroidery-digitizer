import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

import pyembroidery as pe

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from chenille.catalog import inventory, coverage, project_path, create_snapshot, inspect_dst, verify_snapshot


class LibraryCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'assets/private/dst-library/fon2'
        self.folder.mkdir(parents=True)
        self.config = {'source_root': 'assets/private/dst-library',
                       'font_directory_map': {'fon2': 'Font2'},
                       'reference_use': 'owner_authorized_output_example'}

    def write_sample(self, name):
        p = pe.EmbPattern()
        p.add_stitch_absolute(pe.STITCH, 0, 0)
        p.add_stitch_absolute(pe.STITCH, 100, 50)
        p.add_stitch_absolute(pe.END, 100, 50)
        path = self.folder / name
        pe.write_dst(p, str(path))
        return path

    def test_duplicates_keep_all_sources_and_stable_id_after_rename(self):
        path = self.write_sample('Bulldogs330.DST')
        data = path.read_bytes()
        (self.folder / 'copy.dst').write_bytes(data)
        records, folders = inventory(self.root, self.config)
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0]['sources']), 2)
        self.assertEqual(records[0]['sample_id'], 'dst-sha256-' + hashlib.sha256(data).hexdigest())
        self.assertEqual(records[0]['inspection']['metrics']['width_mm'], 10)
        path.rename(self.folder / 'renamed.DST')
        self.assertEqual(inventory(self.root, self.config)[0][0]['sample_id'], records[0]['sample_id'])
        self.assertEqual(folders, {'fon2': 2})

    def test_filename_digits_are_not_verified_design_or_glyphs(self):
        self.write_sample('Bulldogs330.DST')
        records, folders = inventory(self.root, self.config)
        self.assertIsNone(records[0]['verified_design'])
        self.assertIsNone(records[0]['machine_acceptance'])
        report = coverage(records, folders, 'v001')
        self.assertIn('3', report['fonts']['Font2']['filename_character_hints'])
        self.assertEqual(report['fonts']['Font2']['verified_characters'], [])

    def test_bad_file_is_reported_not_silently_skipped(self):
        (self.folder / 'broken.DST').write_bytes(b'bad')
        records, folders = inventory(self.root, self.config)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['inspection']['status'], 'unreadable')
        self.assertEqual(len(coverage(records, folders, 'v001')['unreadable_samples']), 1)

    def test_historical_eof_marker_and_missing_encoded_end_are_distinguished(self):
        path = self.write_sample('reference.DST')
        data = path.read_bytes()
        end = next(i for i in range(512, len(data) - 2, 3) if data[i + 2] & 0xF3 == 0xF3)
        path.write_bytes(data[:end + 3] + b'\x1a')
        self.assertEqual(inspect_dst(path)['flags'], [])
        path.write_bytes(data[:end])
        self.assertIn('missing_encoded_end', inspect_dst(path)['flags'])

    def test_snapshot_roundtrip_and_changed_inputs_are_detected(self):
        import json
        import shutil
        source = self.write_sample('reference.DST')
        original = source.read_bytes()
        repo = Path(__file__).resolve().parents[1]
        for name in ['src/chenille/catalog.py', 'src/chenille/__init__.py', 'scripts/index_library.py']:
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repo / name, destination)
        (self.root / 'config.json').write_text(json.dumps(self.config))
        create_snapshot(self.root, 'config.json', 'v001')
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(verify_snapshot(self.root, 'v001')['source_files'], 1)
        catalog = self.root / 'library/catalog/v001/catalog.json'
        saved = catalog.read_bytes()
        catalog.write_bytes(saved + b' ')
        with self.assertRaisesRegex(ValueError, 'Snapshot checksum'):
            verify_snapshot(self.root, 'v001')
        catalog.write_bytes(saved)
        source.write_bytes(original + b'x')
        with self.assertRaisesRegex(ValueError, 'Source checksum'):
            verify_snapshot(self.root, 'v001')
        source.write_bytes(original)
        (self.folder / 'new.DST').write_bytes(original)
        with self.assertRaisesRegex(ValueError, 'file set changed'):
            verify_snapshot(self.root, 'v001')

    def test_unsafe_paths_and_overwriting_snapshot_rejected(self):
        with self.assertRaises(ValueError):
            project_path(self.root, '../outside')
        import json
        (self.root / 'config.json').write_text(json.dumps(self.config))
        (self.root / 'library/catalog/v001').mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            create_snapshot(self.root, 'config.json', 'v001')
        with self.assertRaises(ValueError):
            create_snapshot(self.root, 'config.json', '../outside')


if __name__ == '__main__':
    unittest.main()
