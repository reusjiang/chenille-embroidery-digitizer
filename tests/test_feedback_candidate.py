import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from generate_dst import write_dst
from build_feedback_candidate import reference_points, compare, reconstruct


class CandidateGuards(unittest.TestCase):
    def test_changed_reference_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'source.DST'
            write_dst(path,np.array([[0,0],[10,0]]))
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            write_dst(path,np.array([[0,0],[20,0]]))
            with self.assertRaisesRegex(ValueError,'checksum'):
                reference_points(path,digest)

    def test_jump_reference_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'source.DST'
            write_dst(path,np.array([[0,0],[10,0],[20,0]]))
            raw=bytearray(path.read_bytes());raw[512+3+2] |= 0x80;path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'continuous'):
                reference_points(path,hashlib.sha256(raw).hexdigest())

    def test_short_core_rejected_before_tie_construction(self):
        with self.assertRaisesRegex(ValueError,'too short'):
            reconstruct(np.array([[0.,0.],[5.,0.]]),330,{'return_length_mm':10})

    def test_comparison_is_translation_invariant_but_not_scale_invariant(self):
        path=np.array([[0.,0.],[10.,0.],[10.,10.]])
        translated=compare(path,path+np.array([100.,50.]))
        self.assertAlmostEqual(translated['bidirectional_p95_max_mm'],0.)
        scaled=compare(path,path*2)
        self.assertGreater(scaled['bidirectional_p95_max_mm'],1.)


if __name__=='__main__': unittest.main()
