import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from zipfile import ZipFile
import pyembroidery as pe
from pyembroidery.DstWriter import encode_record

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from chenille.trial_validation import decode_dst, validate_dst
from chenille.operator_workflow import RULE_DIR, demo, read, save, sha, check, package, verify_rules, initialize

CASE = 'releases/reference-guided/v002/01-F2-Bulldogs'
DST = 'Bulldogs_F2_328.9mm_v002.DST'


class OperatorChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in [*read(ROOT / RULE_DIR / 'manifest.json')['files'], RULE_DIR + '/manifest.json', CASE + '/' + DST, CASE + '/validation.json']:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        demo(self.root, 'fixture')
        self.out = self.root / 'build/operator/fixture'
        self.local = self.root / 'orders/local/fixture'

    def test_complete_demo_and_eof_marker(self):
        report = read(self.out / 'validation.json')
        self.assertTrue(all(report['checks'].values()), report['issues'])
        self.assertTrue(report['demonstration_only'])
        path = self.out / 'candidate.DST'
        path.write_bytes(path.read_bytes() + b'\x1a')
        rows, _ = decode_dst(path)
        self.assertEqual(len(rows), 830)
        # The historical trailer parses, but a changed exact-reuse file must fail identity.
        self.assertFalse(check(self.root, 'fixture')['checks']['exact_reuse_bytes_identical'])

    def test_missing_returns_and_unconfirmed_order_fail(self):
        plan = read(self.out / 'plan.json'); plan['returns'] = []
        save(self.out / 'plan.json', plan)
        order = read(self.local / 'order.json'); order['field_review']['text'] = False
        save(self.local / 'order.json', order)
        report = check(self.root, 'fixture')
        self.assertEqual(report['status'], 'needs_review')
        self.assertFalse(report['checks']['all_stitch_blocks_have_measured_returns'])
        self.assertFalse(report['checks']['order_fields_confirmed'])

    def test_package_rechecks_modified_dst_and_excludes_original_pdf(self):
        pdf = self.local / 'input.pdf'; pdf.write_bytes(b'%PDF-1.4\nlocal private source')
        order = read(self.local / 'order.json')
        order['source'] = {'kind': 'local_pdf', 'path': 'orders/local/fixture/input.pdf', 'sha256': sha(pdf), 'pages': [1]}
        save(self.local / 'order.json', order)
        candidate = self.out / 'candidate.DST'
        candidate.write_bytes(candidate.read_bytes()[:-3])
        target, status = package(self.root, 'fixture')
        self.assertEqual(status, 'needs_review')
        with ZipFile(target) as archive:
            self.assertIsNone(archive.testzip())
            self.assertFalse(any(name.endswith('.pdf') for name in archive.namelist()))
            manifest = json.loads(archive.read('package-manifest.json'))
            for name, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
            self.assertFalse(json.loads(archive.read('validation.json'))['checks']['encoded_structure'])
        second, _ = package(self.root, 'fixture')
        self.assertNotEqual(target, second)

    def test_common_rules_tampering_rejected(self):
        path = self.root / RULE_DIR / 'limits.json'
        limits = read(path); limits['max_stitch_mm'] = 999
        save(path, limits)
        with self.assertRaisesRegex(ValueError, 'Ruleset file changed'):
            verify_rules(self.root)

    def test_return_ranges_cannot_use_middle_or_overlap(self):
        plan = read(self.out / 'plan.json')
        plan['returns'][0]['start_commands_1based'] = [2, 11]
        save(self.out / 'plan.json', plan)
        self.assertFalse(check(self.root, 'fixture')['checks']['all_stitch_blocks_have_measured_returns'])

    def test_experiment_requires_saved_implementation(self):
        plan = read(self.out / 'plan.json'); plan['route'] = 'experimental'
        save(self.out / 'plan.json', plan)
        report = check(self.root, 'fixture')
        self.assertFalse(report['checks']['implementation_recorded'])
        self.assertFalse(report['checks']['experimental_hypotheses_recorded'])

    def test_pdf_initialization_copies_input_and_rejects_reused_job(self):
        pdf = self.root / 'source.pdf'
        pdf.write_bytes(b'%PDF-1.4\nfixture only; not a rendered order')
        local, out = initialize(self.root, 'local-pdf', pdf)
        self.assertEqual((local / 'input.pdf').read_bytes(), pdf.read_bytes())
        order = read(local / 'order.json')
        self.assertEqual(order['source']['sha256'], sha(pdf))
        self.assertIsNone(order['design']['text'])
        self.assertTrue((out / 'implementation').is_dir())
        with self.assertRaisesRegex(ValueError, 'already exists'):
            initialize(self.root, 'local-pdf', pdf)

    def test_field_contradiction_and_changed_candidate_are_not_accepted(self):
        order = read(self.local / 'order.json')
        order['design']['lines'] = ['Different word']
        save(self.local / 'order.json', order)
        self.assertFalse(check(self.root, 'fixture')['checks']['order_fields_confirmed'])
        candidate = self.out / 'candidate.DST'
        candidate.write_bytes(candidate.read_bytes() + b'\x1a')
        self.assertFalse(check(self.root, 'fixture')['checks']['candidate_unchanged_for_this_job'])

    def test_missing_pdf_yields_diagnostic_report(self):
        order = read(self.local / 'order.json')
        order['source'] = {'kind': 'local_pdf', 'path': 'orders/local/fixture/input.pdf', 'sha256': '0' * 64}
        save(self.local / 'order.json', order)
        self.assertFalse(check(self.root, 'fixture')['checks']['order_input_hash'])

    def test_each_stitch_block_needs_its_own_returns(self):
        # Two 30 mm stitch runs separated by a 10 mm jump, all dimensions in 0.1 mm.
        rows = [[x, 0, pe.STITCH] for x in range(0, 301, 10)]
        rows += [[400, 0, pe.JUMP]]
        rows += [[x, 0, pe.STITCH] for x in range(400, 701, 10)]
        header = f'LA:two-blocks      \rST:{len(rows)+1:7}\rCO:  0\r+X:  700\r-X:    0\r+Y:    0\r-Y:    0\rAX:  +700\rAY:    +0\r'
        data = (header.encode() + b'\x1a').ljust(512, b' ')
        previous = 0
        for x, y, command in rows:
            data += bytes(encode_record(x - previous, 0, command))
            previous = x
        data += b'\x00\x00\xf3'
        candidate = self.root / 'two-blocks.DST'; candidate.write_bytes(data)
        order = read(self.local / 'order.json'); order['design']['width_mm'] = 70
        plan = read(self.out / 'plan.json')
        plan['returns'] = [
            {'start_commands_1based': [1, 11], 'end_commands_1based': [21, 31]},
            {'start_commands_1based': [33, 43], 'end_commands_1based': [53, 63]}]
        limits = read(self.root / RULE_DIR / 'limits.json')
        report, _ = validate_dst(candidate, order, plan, limits)
        self.assertTrue(all(report['checks'].values()), report)
        plan['returns'].pop()
        self.assertFalse(validate_dst(candidate, order, plan, limits)[0]['checks']['all_stitch_blocks_have_measured_returns'])



if __name__ == '__main__':
    unittest.main()
