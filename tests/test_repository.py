import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from project import BASELINE,ROOT,SOURCE,SOURCE_SHA256,output_path
from verify_release import verify_release


class HandoffTests(unittest.TestCase):
    def test_reviewed_source_unchanged(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),SOURCE_SHA256)
    def test_frozen_dst_unchanged(self):
        self.assertEqual(hashlib.sha256((BASELINE/'Bulldogs_F2_330mm.DST').read_bytes()).hexdigest(),
                         'fd76864135643559e075c8cc5ea224a67472f2c21b7873889c3506576461e092')
    def test_release_integrity(self):
        self.assertEqual(verify_release(BASELINE)['release_id'],'BULL-F2-330-v001')
    def test_frozen_output_rejected(self):
        with self.assertRaises(ValueError):output_path(str(BASELINE))
        with self.assertRaises(ValueError):output_path('build/../releases/new')
    def test_modified_release_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);name='Bulldogs_F2_330mm.DST';(p/name).write_bytes(b'bad')
            (p/'manifest.json').write_text(json.dumps({'files':{name:{'bytes':3,'sha256':'0'*64}}}))
            with self.assertRaisesRegex(ValueError,'SHA256'):verify_release(p)
    def test_feedback_points_to_release(self):
        t=json.loads((ROOT/'feedback/templates/trial-record.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((ROOT/t['generated_dst']).read_bytes()).hexdigest(),t['generated_dst_sha256'])
        self.assertEqual(t['status'],'not_run')

if __name__=='__main__':unittest.main()
