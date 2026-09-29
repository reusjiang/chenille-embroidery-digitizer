import tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pyembroidery as pe
from generate_dst import write_dst,raw_decode

class DSTValidation(unittest.TestCase):
    def test_signed_axes_and_record_extremes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'axes.DST';pts=np.array([[0,0],[121,-121],[0,0],[-121,121],[0,0]])
            write_dst(p,pts);a,h=raw_decode(p)
            self.assertTrue(np.array_equal(a[:-1,:2],pts))
            b=np.array(pe.read_dst(str(p),{'trim_at':False,'clipping':False}).stitches)
            self.assertTrue(np.array_equal(a,b))
    def test_truncated_end_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.DST';write_dst(p,np.array([[0,0],[10,0]]));p.write_bytes(p.read_bytes()[:-3])
            with self.assertRaises(AssertionError):raw_decode(p)
    def test_header_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.DST';write_dst(p,np.array([[0,0],[10,0]]))
            p.write_bytes(p.read_bytes().replace(b'+X:   10',b'+X:   11'))
            with self.assertRaises(AssertionError):raw_decode(p)
    def test_excessive_delta_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(AssertionError):write_dst(Path(d)/'bad.DST',np.array([[0,0],[122,0]]))

if __name__=='__main__':unittest.main()
