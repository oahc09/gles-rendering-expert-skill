#!/usr/bin/env python3
import argparse
from catalog import build,write
from check_coverage import extensions
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sources',default='references/coverage/source-manifest.json');p.add_argument('--output',default='references/coverage/gles-api-catalog.json');p.add_argument('--extensions-output',default='references/coverage/extensions-catalog.json');a=p.parse_args();gles=build(a.sources,'gles');write(a.output,gles);write(a.extensions_output,extensions(gles,build(a.sources,'egl')))
