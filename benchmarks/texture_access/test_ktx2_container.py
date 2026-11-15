import struct,unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from ktx2_container import parse,MAGIC

def valid():
 dfd=struct.pack('<IIHH4B4B8B',92,0,2,88,1,1,1,0,0,0,0,0,4,0,0,0,0,0,0,0)+b''.join(struct.pack('<HBB4BII',i*8,7,c,0,0,0,0,0,255) for i,c in enumerate((0,1,2,15)))
 return bytearray(MAGIC+struct.pack('<13I2Q',37,1,1,1,0,0,1,1,0,104,92,0,0,0,0)+struct.pack('<3Q',196,4,4)+dfd+bytes([1,2,3,255]))
class Container(unittest.TestCase):
 def test_valid(self):self.assertEqual(parse(valid())['payload'],bytes([1,2,3,255]))
 def test_truncations(self):
  for n in [0,12,79,80,103,120,151]:
   with self.subTest(n=n),self.assertRaises(ValueError):parse(valid()[:n])
 def test_header_mutations(self):
  for offset,value in [(0,0),(12,42),(16,2),(20,0),(28,1),(32,1),(36,6),(40,2),(44,1),(48,80),(52,0),(80,0),(88,0),(96,3),(116,162),(118,2),(120,3),(124,8)]:
   d=valid();d[offset]=value
   with self.subTest(offset=offset),self.assertRaises(ValueError):parse(d)
if __name__=='__main__':unittest.main()
