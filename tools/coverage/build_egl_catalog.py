#!/usr/bin/env python3
import argparse
from catalog import build,write
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sources',default='references/coverage/source-manifest.json');p.add_argument('--output',default='references/coverage/egl-api-catalog.json');a=p.parse_args();write(a.output,build(a.sources,'egl'))
