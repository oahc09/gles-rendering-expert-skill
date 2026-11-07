#!/usr/bin/env python3
"""Validate schema/semantic pipeline fixtures; not a substitute for GLES execution."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PIPE = ROOT / 'benchmarks/pipeline'
sys.path.insert(0, str(PIPE))
import material
import rendergraph
import shader_risks
import variants

def run():
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return {'status':'BLOCKED_BY_TOOLCHAIN','reason':'Install jsonschema>=4.23 to validate Draft 2020-12 schemas','cases':[]}
    schemas = {}
    for path in sorted((PIPE/'schemas').glob('*.schema.json')):
        schema = json.loads(path.read_text())
        Draft202012Validator.check_schema(schema)
        schemas[path.stem.removesuffix('.schema')] = Draft202012Validator(schema)
    rows = []
    for name, filename, validator in [('variant','variants.json',variants.validate),('material','material.json',material.validate)]:
        for case in json.loads((PIPE/'cases'/filename).read_text()):
            schema_errors = [e.message for e in schemas[name].iter_errors(case['input'])]
            try: semantic_errors = validator(case['input'])
            except (ValueError, TypeError) as exc: semantic_errors = [str(exc)]
            actual_valid = not schema_errors and not semantic_errors
            rows.append({'id':case['id'],'expected_valid':case['valid'],'schema_errors':schema_errors,
                         'semantic_errors':semantic_errors,'status':'PASS' if actual_valid == case['valid'] else 'FAIL'})
    for path in sorted((PIPE/'cases/graphs').glob('*.json')):
        case = json.loads(path.read_text())
        schema_errors = [e.message for e in schemas['rendergraph'].iter_errors(case['input'])]
        result = rendergraph.check(case['input'])
        accepted = not schema_errors and result['valid']
        expected_rule = case.get('expected_rule')
        matched = not expected_rule or expected_rule in [e['rule'] for e in result['errors']]
        rows.append({'id':path.stem,'expected_valid':case['expected_valid'],'schema_errors':schema_errors,
                     'semantic_errors':result['errors'],
                     'status':'PASS' if accepted == case['expected_valid'] and matched else 'FAIL'})
    for case in json.loads((PIPE/'cases/shader-risk-experiments.json').read_text()):
        report = shader_risks.analyze(case['source_a'],case['id'],case['stage'],variant_count=case['variant_count'])
        errors = [e.message for e in schemas['shader-risk-report'].iter_errors(report)]
        rows.append({'id':case['id'],'schema_errors':errors,'status':'FAIL' if errors else 'PASS'})
    return {'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',
            'scope':'Draft 2020-12 schemas and authored semantic controls, not GL/device/model results',
            'schemas':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((PIPE/'schemas').glob('*.schema.json'))},
            'cases':rows}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('reports/pipeline-contracts.json'))
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'cases':len(result['cases'])}))
    raise SystemExit(0 if result['status']=='PASS' else 2)
