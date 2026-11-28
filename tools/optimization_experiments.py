"""Closed registry of executable, bounded host experiments. Never executes commands."""
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DISCARD_EXPERIMENT = 'discard-depth-after-consumer-v1'
STRATEGY_EXPERIMENTS = {
    'discard-dead-attachment': DISCARD_EXPERIMENT,
    'fence-ring-reuse': 'fence-ring-reuse-v113',
    'texture-mip-selection': 'texture-mip-selection-v113',
    'resolve-msaa-once': 'resolve-msaa-once-v113',
    'compute-to-fragment': 'compute-to-fragment-v113',
    'coherent-framebuffer-fetch': 'coherent-framebuffer-fetch-v113',
}
EXPERIMENT_STRATEGIES = {experiment: strategy for strategy, experiment in STRATEGY_EXPERIMENTS.items()}
EXPECTED_OUTCOMES = ('HOST_PASS', 'QUALITY_FAIL', 'BLOCKED')
REGISTRY={
 'rgba8-graph-scale-replay-v1':('benchmarks/pipeline/candidate_replay.py','finite three-pass RGBA8 graph scaling and quality fallback; no physical performance'),
 'shader-advanced-v1':('benchmarks/shader_ab/advanced.py','bounded UBO/SSBO/discard/depth correctness; no timing'),
 'texture-access-v1':('benchmarks/texture_access/run.py','finite texture mechanism/quality controls; no hardware gain'),
 'postfx-resolution-loss-v1':('benchmarks/pipeline/postfx_quality.py','finite texture-resolution quality oracle, not general PostFX equivalence'),
}
REGISTRY.update({experiment: ('benchmarks/workflow/strategies.py', f'fixed 4x4 software GLES {strategy} control')
                 for strategy, experiment in STRATEGY_EXPERIMENTS.items()})


def outcome_exit_code(status, expected=None):
    if expected is not None:
        return 0 if status == expected else 1
    if status in {'HOST_PASS', 'HOST_WORKFLOW_PASS'}:
        return 0
    return 3 if status == 'BLOCKED' else 1

def resolve(experiment):
    if not isinstance(experiment,str) or experiment not in REGISTRY:return None
    relative,scope=REGISTRY[experiment]; path=(ROOT/relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():return None
    argv = ['python3', relative, '--config', 'DRIVER_JSON', '--output', 'REPORT_JSON']
    if experiment in EXPERIMENT_STRATEGIES:
        argv += ['--strategy', EXPERIMENT_STRATEGIES[experiment]]
    return {'id':experiment,'source':relative,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'argv':argv,
            'scope':scope,'execution':'NOT_RUN_BY_ADVISOR','report_policy':'Keep raw reports private; sanitize host metadata before publication','requires':['configured GLES driver','explicit operator execution']}
