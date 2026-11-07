"""GLES whole-resource access checker. Barriers describe consumer access classes."""
import argparse
import json
from pathlib import Path

BITS = {'ssbo': 'GL_SHADER_STORAGE_BARRIER_BIT', 'image': 'GL_SHADER_IMAGE_ACCESS_BARRIER_BIT', 'sample': 'GL_TEXTURE_FETCH_BARRIER_BIT', 'vertex': 'GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT', 'index': 'GL_ELEMENT_ARRAY_BARRIER_BIT', 'indirect': 'GL_COMMAND_BARRIER_BIT', 'framebuffer': 'GL_FRAMEBUFFER_BARRIER_BIT', 'uniform': 'GL_UNIFORM_BARRIER_BIT', 'texture_update': 'GL_TEXTURE_UPDATE_BARRIER_BIT', 'buffer_update': 'GL_BUFFER_UPDATE_BARRIER_BIT'}

def check(trace):
    errors, warnings, pending = [], [], {}
    if not isinstance(trace, dict) or not isinstance(trace.get('events'), list):
        return dict(valid=False, errors=[dict(rule='HZ_SCHEMA', path='/', message='Trace object requires events array')], warnings=[])
    for i, event in enumerate(trace['events']):
        if not isinstance(event, dict) or not isinstance(event.get('accesses', []), list) or any(not isinstance(a, dict) for a in event.get('accesses', [])) or not isinstance(event.get('barrier', []), list) or any(not isinstance(b, str) for b in event.get('barrier', [])) or not isinstance(event.get('sync', {}), dict):
            return dict(valid=False, errors=[dict(rule='HZ_SCHEMA', path='/events/' + str(i), message='Invalid event/access/barrier/sync shape')], warnings=[])
    for i, event in enumerate(trace['events']):
        sync = event.get('sync', {})
        if any(k in sync and type(sync[k]) is not bool for k in ('fence_after_write','producer_flush','consumer_wait','consumer_rebind')):
            return dict(valid=False, errors=[dict(rule='HZ_SCHEMA', path='/events/' + str(i) + '/sync', message='Synchronization flags require booleans')], warnings=[])
    version = trace.get('gles', '3.0')
    def issue(rule, i, resource, message, **extra):
        errors.append(dict(rule=rule, path='/events/' + str(i), resource=resource, message=message, **extra))
    if version not in ('3.0', '3.1', '3.2'):
        issue('HZ_VERSION', 0, '', 'Supported GLES versions: 3.0, 3.1, 3.2')
    for i, event in enumerate(trace.get('events', [])):
        barriers = event.get('barrier', [])
        if barriers and version == '3.0':
            issue('HZ_VERSION', i, '', 'glMemoryBarrier requires GLES 3.1 in this core-only model')
        for bit in barriers:
            if bit not in set(BITS.values()) | {'GL_ALL_BARRIER_BITS'}:
                issue('HZ_BARRIER_BIT', i, '', 'Unknown barrier: ' + bit)
        for state in pending.values():
            if state['context'] == event.get('context', 'main'):
                state['bits'].update(barriers)
        accesses = event.get('accesses', [])
        for a in accesses:
            r, kind, mode = a.get('resource'), a.get('kind'), a.get('mode')
            context = event.get('context', 'main')
            if not isinstance(r, str) or not isinstance(kind, str) or kind not in BITS or mode not in ('read', 'write', 'readwrite'):
                issue('HZ_SCHEMA', i, r, 'Known resource, access kind and mode required')
                continue
            if a.get('subrange') is not None:
                warnings.append(dict(rule='HZ_SUBRANGE_CONSERVATIVE', path='/events/' + str(i), resource=r, message='Ranges not analyzed: whole-resource overlap assumed'))
            if (kind in ('ssbo', 'image', 'indirect') or a.get('stage') == 'compute') and version == '3.0':
                issue('HZ_VERSION', i, r, 'Access requires GLES 3.1 core')
            if kind == 'sample' and any(b.get('resource') == r and b.get('kind') == 'framebuffer' and b.get('mode') != 'read' for b in accesses):
                issue('HZ_FEEDBACK', i, r, 'Framebuffer/sample feedback is undefined; memory barrier does not repair it')
            old = pending.get(r)
            if old:
                if old['context'] != context and context not in old['visible_to']:
                    sync = event.get('sync', {})
                    if not (sync.get('producer') == old['context'] and sync.get('fence_after_write') and sync.get('producer_flush') and sync.get('consumer_wait') and sync.get('consumer_rebind')):
                        issue('HZ_CONTEXT_SYNC', i, r, 'Cross-context sharing requires producer fence+flush, consumer wait and object visibility/rebind contract')
                    else:
                        old['visible_to'].add(context)
                if old['shader']:
                    required = BITS[kind]
                    if required not in old['bits'] and 'GL_ALL_BARRIER_BITS' not in old['bits']:
                        issue('HZ_BARRIER', i, r, 'Missing shader-write visibility barrier before consumer', required_barrier=required, producer_stage=old['stage'], consumer_stage=a.get('stage', 'unspecified'))
        # Commit writes only after checking entire command: same-command shader access
        # cannot be made safe by a command-level barrier.
        for a in accesses:
            if a.get('mode') in ('write', 'readwrite') and isinstance(a.get('resource'), str):
                pending[a['resource']] = dict(shader=a.get('kind') in ('ssbo', 'image'), context=event.get('context', 'main'), stage=a.get('stage', 'unspecified'), bits=set(), visible_to=set())
        if event.get('intra_dispatch_dependency'):
            warnings.append(dict(rule='HZ_DYNAMIC', path='/events/' + str(i), message='Invocation overlap and shader memory model require shader inspection; command barriers cannot order workgroups'))
    return dict(valid=not errors, errors=errors, warnings=warnings, model='whole-resource conservative static', device_evidence='NOT_RUN')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    result = check(json.loads(parser.parse_args().trace.read_text()))
    print(json.dumps(result, indent=2))
    return 0 if result['valid'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
