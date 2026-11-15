"""Closed registry of executable, bounded host experiments. Never executes commands."""
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REGISTRY={
 'shader-advanced-v1':('benchmarks/shader_ab/advanced.py','bounded UBO/SSBO/discard/depth correctness; no timing'),
 'texture-access-v1':('benchmarks/texture_access/run.py','finite texture mechanism/quality controls; no hardware gain'),
 'postfx-resolution-loss-v1':('benchmarks/pipeline/postfx_quality.py','finite texture-resolution quality oracle, not general PostFX equivalence'),
}

def resolve(experiment):
    if not isinstance(experiment,str) or experiment not in REGISTRY:return None
    relative,scope=REGISTRY[experiment]; path=(ROOT/relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():return None
    return {'id':experiment,'source':relative,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'argv':['python3',relative,'--config','DRIVER_JSON','--output','REPORT_JSON'],
            'scope':scope,'execution':'NOT_RUN_BY_ADVISOR','report_policy':'Keep raw reports private; sanitize host metadata before publication','requires':['configured GLES driver','explicit operator execution']}
