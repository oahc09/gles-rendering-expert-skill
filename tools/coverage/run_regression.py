"""Thin reuse of the existing manifest runner, with the v1.1.0 test directory set."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from run_v109_regression import run
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=run(json.loads((ROOT/'docs/v1.1.0/test-manifest.json').read_text()));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}));raise SystemExit(result['status']!='PASS')
