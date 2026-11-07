"""Ten isolated CPU reproductions. These do not claim device-driver reproduction."""
import json
from pathlib import Path
import rendergraph
import hazards
import variants
import material

ROOT = Path(__file__).parent

def fixture(folder, name):
    return json.loads((ROOT / 'cases' / folder / (name + '.json')).read_text())['input']

def reproduce():
    rows = []
    def add(name, symptom, capture, broken, fixed, cause, fix, regression):
        rows.append(dict(id=name, symptom=symptom, capture=capture, minimal_reproduction={'broken':broken,'fixed':fixed}, root_cause=cause, fix=fix, regression=regression, reproduced=bool(broken and fixed), evidence='CPU_MODEL_REPRODUCED', hardware='NOT_RUN'))
    bad={'gles':'3.0','quality':'low','features':['compute'],'macros':{'COMPUTE':'1'}}
    good=dict(bad,gles='3.1')
    add('variant_macro','Compute variant fails on ES 3.0','Record GLES version, macros and source', bool(variants.validate(bad)), not variants.validate(good), 'Feature macro selects unsupported core compute stage', 'Gate feature on probed ES 3.1; use ES 3.0 graphics fallback', 'Variant validator rejects unsupported feature')
    device=dict(vendor='fixture',renderer='cpu',version='3.1',driver='1',backend='native_gles',material_abi='Material-v1',extensions=[])
    key=variants.cache_key('source',{},[],device)
    new=variants.cache_key('source',{},[],dict(device,driver='2'))
    add('cache_invalid','Program binary fails after driver change','Capture binary format, GL_LINK_STATUS and cache identity',key != new,key == variants.cache_key('source',{},[],device),'Driver identity changed','Invalidate key and recompile source','Driver changes key; identical identity is stable')
    members,_=material.layout_members([{'name':'x','type':'float'},{'name':'color','type':'vec4'}],'std140')
    add('material_abi','Wrong material color','Compare reflected offsets with host manifest',members[1]['offset'] != 4,members[1]['offset'] == 16,'vec4 std140 alignment is 16, not packed offset 4','Pad host struct and verify reflection','Calculated color offset is 16')
    for name,bad_file,good_file,cause,fix in [('fbo_feedback','06_feedback','01_sequential','Read and write attachment in same pass','Ping-pong distinct textures'),('msaa_resolve','10_resolve_bad_size','09_resolve','Resolve rectangles have different dimensions','Equal size/format, NEAREST and single-sample destination')]:
        bad=rendergraph.check(fixture('graphs',bad_file)); good=rendergraph.check(fixture('graphs',good_file))
        add(name,'Invalid or undefined image','Capture FBO attachments and pass graph',not bad['valid'],good['valid'],cause,fix,'Negative graph fails; corrected graph passes')
    bad=hazards.check(fixture('hazards','03_missing_sample'));good=hazards.check(fixture('hazards','04_valid_sample'))
    add('barrier_missing','Stale compute-produced texture','Capture dispatch, image binding, barrier and sample',not bad['valid'],good['valid'],'Image writes not visible to texture fetch','GL_TEXTURE_FETCH_BARRIER_BIT after dispatch','Consumer-specific barrier accepted')
    def encode(x):return 12.92*x if x<=.0031308 else 1.055*x**(1/2.4)-.055
    value=.18; correct=encode(value); double=encode(correct)
    add('double_srgb','Washed out midtones','Record attachment encoding and shader output',abs(double-correct)>.2,abs(correct-.461356)<1e-5,'Manual encoding plus sRGB attachment conversion','Encode exactly once','Piecewise sRGB CPU oracle tolerance 1e-5')
    alpha=.25; straight=.8; correct=straight*alpha; wrong=correct*alpha
    add('alpha_edge','Dark transparent edges','Record blend factors and texture alpha convention',abs(wrong-correct)>.1,abs(correct-.2)<1e-8,'Premultiplied RGB multiplied by alpha twice','Premultiply once with ONE, ONE_MINUS_SRC_ALPHA','Single multiplication reference')
    hdr=4.; tone=lambda x:x/(1+x)
    add('hdr_clip','Lost highlights','Capture pre-tone-map attachment format',abs(tone(min(hdr,1))-tone(hdr))>.2,abs(tone(hdr)-.8)<1e-8,'UNORM intermediate clips HDR before tone mapping','Use renderable HDR intermediate and validate support','4.0 maps to 0.8 before display encoding')
    attempts=[]
    def compile_source(): attempts.append('compile');return True
    result=variants.load_program(None,key,[1],lambda *args:False,compile_source)
    cold = len(attempts) == 1 and result['path'] == 'source'
    warm = variants.load_program({'key':key,'format':1,'binary':b'fixture'},key,[1],lambda *args:True,compile_source)
    add('startup_compile','Cold startup compilation work','Count compile callbacks; real timing requires trace',cold, warm['path'] == 'binary' and len(attempts) == 1,'Cache miss invokes source compilation','Warm permitted variants asynchronously and collect real cold/warm traces','Cold miss compiles; valid warm cache bypasses compile; no invented timing')
    return rows

if __name__ == '__main__':
    rows=reproduce();print(json.dumps(rows,indent=2));raise SystemExit(0 if all(r['reproduced'] for r in rows) else 1)
