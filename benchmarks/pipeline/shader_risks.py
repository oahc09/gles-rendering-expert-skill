"""Lexical, conservative hypotheses only; never substitutes for compiler/profiler."""
import argparse
import json
import re

def analyze(source, shader='inline', stage='fragment', device='UNSPECIFIED', variant_count=1):
    if not isinstance(source, str) or not source.strip(): raise ValueError('nonempty shader source required')
    if stage not in ('vertex','fragment','compute','geometry','tess_control','tess_evaluation'): raise ValueError('invalid shader stage')
    if not isinstance(shader,str) or not shader or not isinstance(device,str) or not device: raise ValueError('shader/device required')
    if type(variant_count) is not int or variant_count < 1: raise ValueError('variant_count must be positive integer')
    # Preserve line numbers while removing comments. No macro expansion or data-flow claims.
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', lambda m: '\n' * m[0].count('\n'), source, flags=re.S)
    lines = clean.splitlines(); risks=[]
    def add(rule,line,hypothesis,experiment):
        risks.append(dict(rule=rule,shader=shader,stage=stage,line=line,device_condition=device,hypothesis=hypothesis,experiment=experiment,evidence='STATIC_HEURISTIC',measurement_status='NOT_RUN'))
    samples=[]; declarations=[]; outputs=[]
    for number,line in enumerate(lines,1):
        if re.search(r'\btexture(?:Lod|Grad|Proj|Offset)?\s*\(',line): samples.append(number)
        if re.search(r'\btexture\w*\s*\(\s*\w+\s*\[\s*[A-Za-z_]',line): add('DYNAMIC_SAMPLER_INDEX',number,'Sampler array index may be dynamic or illegal in this GLSL ES version.','Compile both variants; compare constant-index selection only after legality check.')
        if re.search(r'\bif\s*\(',line): add('POSSIBLE_NONUNIFORM_BRANCH',number,'Branch may diverge; uniformity is not inferred.','Compare branch and equivalent select with coherent and incoherent inputs.')
        if re.search(r'\b(?:[biu]?vec[234]|mat[234])\s+\w+',line): declarations.append(number)
        if re.search(r'layout\s*\([^)]*location\s*=\s*[1-9]\d*[^)]*\)\s*out\b',line): outputs.append(number)
        if re.search(r'\b(?:for|while)\s*\(',line) and re.search(r'\btexture\w*\s*\(',line): add('TEXTURE_IN_LOOP',number,'Texture samples inside a loop may amplify bandwidth.','Reduce taps with equivalent image quality and compare GPU time/bandwidth.')
    if len(samples)>=4: add('HIGH_TEXTURE_FREQUENCY',samples[3],'Four or more source lines sample textures; runtime frequency is unknown.','Compare tap reduction at fixed resolution and visual tolerance.')
    if len(declarations)>=16: add('REGISTER_PRESSURE_HYPOTHESIS',declarations[15],'Many vector declarations may increase live ranges; occupancy is not measured.','Use compiler statistics and profiler occupancy; shorten live ranges and compare.')
    for line in outputs: add('MRT_BANDWIDTH_HYPOTHESIS',line,'Additional output may be needed; redundancy cannot be established lexically.','Remove only unused targets; compare bandwidth and complete downstream output.')
    if variant_count>128: add('VARIANT_BUDGET',1,'Variant cardinality may increase build/startup costs.','Record cold/warm compile-link time, binary size and cache hit rate.')
    return dict(schema_version=1,shader=shader,stage=stage,measurement_status='NOT_RUN',limitations=['Lexical scan only; macros, data flow, register allocation and device performance are not inferred.'],risks=risks)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('shader'); parser.add_argument('--stage',default='fragment'); parser.add_argument('--device',default='UNSPECIFIED'); args=parser.parse_args()
    try: print(json.dumps(analyze(open(args.shader).read(),args.shader,args.stage,args.device),indent=2))
    except (ValueError,OSError) as exc: parser.exit(2,str(exc)+'\n')
