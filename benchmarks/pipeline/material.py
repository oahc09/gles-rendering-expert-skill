"""Restricted flat scalar/vector/matrix material ABI, not a general GLSL parser."""
import argparse
import json

TYPES = {'float': (4,4), 'int': (4,4), 'uint': (4,4), 'vec2': (8,8), 'vec3': (16,12), 'vec4': (16,16),
         'ivec2': (8,8), 'ivec3': (16,12), 'ivec4': (16,16), 'mat2': (8,16), 'mat3': (16,48), 'mat4': (16,64)}
FORMATS = {'sampler2D': {'RGBA8','SRGB8_ALPHA8','RGBA16F','R8'}, 'samplerCube': {'RGBA8','SRGB8_ALPHA8','RGBA16F'},
           'isampler2D': {'RGBA8I','R32I'}, 'usampler2D': {'RGBA8UI','R32UI'}, 'sampler2DShadow': {'DEPTH_COMPONENT16','DEPTH_COMPONENT24'}}

def align(n, a): return (n + a - 1) // a * a

def integer(value, label, minimum=0):
    if type(value) is not int or value < minimum: raise ValueError(label + ' must be integer >= ' + str(minimum))
    return value

def layout_members(members, layout):
    if layout not in ('std140', 'std430'): raise ValueError('unknown layout')
    if not isinstance(members, list) or not members: raise ValueError('members must be nonempty array')
    offset, maximum, result, names = 0, 16 if layout == 'std140' else 1, [], set()
    for member in members:
        if not isinstance(member, dict): raise ValueError('member must be object')
        name, kind = member.get('name'), member.get('type')
        if not isinstance(name, str) or not name or name in names: raise ValueError('duplicate/invalid member name')
        names.add(name)
        if not isinstance(kind, str) or kind not in TYPES: raise ValueError(name + ': unsupported type (flat column-major only)')
        if member.get('row_major', False): raise ValueError(name + ': row_major unsupported')
        alignment, size = TYPES[kind]; matrix_stride = 0
        if kind.startswith('mat'):
            columns = int(kind[-1]); matrix_stride = align(TYPES['vec' + str(columns)][0], 16) if layout == 'std140' else TYPES['vec' + str(columns)][0]
            alignment = matrix_stride; size = columns * matrix_stride
        stride = 0
        if 'array' in member:
            count = integer(member['array'], name + '.array', 1)
            alignment = align(alignment, 16) if layout == 'std140' else alignment
            stride = align(size, alignment); size = count * stride
        offset = align(offset, alignment); maximum = max(maximum, alignment)
        result.append(dict(name=name, type=kind, offset=offset, array_stride=stride, matrix_stride=matrix_stride))
        offset += size
    return result, align(offset, maximum)

def validate(manifest, reflection=None, baseline=None):
    if not isinstance(manifest, dict) or manifest.get('gles') not in ('3.0','3.1','3.2'): raise ValueError('gles must be 3.0/3.1/3.2')
    errors, bindings, names = [], set(), set()
    for key in ('blocks', 'samplers'):
        if not isinstance(manifest.get(key), list): raise ValueError(key + ' must be array')
    for block in manifest['blocks']:
        if not isinstance(block, dict): raise ValueError('block must be object')
        name = block.get('name')
        if not isinstance(name, str) or not name or name in names: raise ValueError('duplicate/invalid block name')
        names.add(name); kind = block.get('kind'); layout = block.get('layout')
        if kind not in ('ubo','ssbo'): raise ValueError(name + ': kind must be ubo/ssbo; GLES has no descriptor sets')
        if 'set' in block: errors.append(name + ':DESCRIPTOR_SET_NOT_GLES')
        if kind == 'ubo' and layout != 'std140': errors.append(name + ':UBO_REQUIRES_STD140_CONTRACT')
        if kind == 'ssbo' and manifest['gles'] < '3.1': errors.append(name + ':SSBO_REQUIRES_GLES_3.1')
        binding = integer(block.get('binding'), name + '.binding')
        if (kind,binding) in bindings: errors.append(name + ':BINDING_COLLISION:' + str(binding))
        bindings.add((kind,binding))
        expected, size = layout_members(block.get('members'), layout)
        if integer(block.get('size'), name + '.size') != size: errors.append(name + ':BLOCK_SIZE:expected ' + str(size))
        for actual, want in zip(block['members'], expected):
            for field in ('offset','array_stride','matrix_stride'):
                if field == 'offset' or field in actual:
                    if integer(actual.get(field), name + '.' + actual['name'] + '.' + field) != want[field]: errors.append(name + '.' + actual['name'] + ':' + field.upper() + ':expected ' + str(want[field]))
        limit = manifest.get('max_' + kind + '_bindings')
        if limit is not None and binding >= integer(limit, 'binding limit', 1): errors.append(name + ':BINDING_LIMIT')
    units, sampler_names = {}, set()
    limit = integer(manifest.get('max_texture_units', 16), 'max_texture_units', 1)
    for sampler in manifest['samplers']:
        if not isinstance(sampler, dict): raise ValueError('sampler must be object')
        name = sampler.get('name')
        if not isinstance(name, str) or not name or name in sampler_names: raise ValueError('duplicate/invalid sampler name')
        sampler_names.add(name); kind = sampler.get('type'); unit = integer(sampler.get('unit'), name + '.unit')
        if not isinstance(kind, str) or kind not in FORMATS: raise ValueError(name + ': unsupported sampler type')
        if unit >= limit: errors.append(name + ':TEXTURE_UNIT_LIMIT:' + str(unit))
        if unit in units and units[unit] != kind: errors.append(name + ':SAMPLER_TYPE_COLLISION:' + str(unit))
        units[unit] = kind
        if not isinstance(sampler.get('format'), str) or sampler.get('format') not in FORMATS[kind]: errors.append(name + ':TEXTURE_FORMAT_MISMATCH')
    interfaces = manifest.get('interfaces', [])
    if not isinstance(interfaces, list): raise ValueError('interfaces must be array')
    seen_interfaces = set()
    for interface in interfaces:
        if not isinstance(interface, dict): raise ValueError('interface must be object')
        name = interface.get('name')
        if not isinstance(name, str) or not name or name in seen_interfaces: raise ValueError('duplicate/invalid interface name')
        seen_interfaces.add(name)
        producer, consumer = interface.get('producer'), interface.get('consumer')
        if not isinstance(producer, dict) or not isinstance(consumer, dict): raise ValueError(name + ': producer/consumer required')
        for endpoint in (producer, consumer):
            if not isinstance(endpoint.get('type'), str) or endpoint.get('type') not in TYPES: raise ValueError(name + ': unsupported interface type')
            integer(endpoint.get('array', 1), name + '.array', 1)
        if any(producer.get(field, default) != consumer.get(field, default) for field, default in [('type', None), ('array', 1), ('interpolation', 'smooth')]):
            errors.append(name + ':SHADER_INTERFACE_MISMATCH')
    # A location is a reflected linked-program value, never a portable ABI offset.
    for sampler in manifest['samplers']:
        if 'location' in sampler:
            integer(sampler['location'], sampler['name'] + '.location')
    if reflection is not None:
        if not isinstance(reflection, dict) or not isinstance(reflection.get('blocks'), list): raise ValueError('reflection.blocks required')
        if any(not isinstance(b, dict) or not isinstance(b.get('name'), str) for b in reflection['blocks']): raise ValueError('reflection block name required')
        if len({b['name'] for b in reflection['blocks']}) != len(reflection['blocks']): raise ValueError('duplicate reflection block')
        observed = {b['name']: b for b in reflection['blocks']}
        for block in manifest['blocks']:
            actual = observed.get(block['name'])
            if actual is None: errors.append(block['name'] + ':REFLECTION_BLOCK_MISSING'); continue
            for field in ('size','binding'):
                if actual.get(field) != block[field]: errors.append(block['name'] + ':REFLECTION_' + field.upper())
            reflected_members = actual.get('members', [])
            if not isinstance(reflected_members, list) or any(not isinstance(m, dict) or not isinstance(m.get('name'), str) for m in reflected_members): raise ValueError('reflection members must have names')
            if len({m['name'] for m in reflected_members}) != len(reflected_members): raise ValueError('duplicate reflection member')
            members = {m['name']:m for m in reflected_members}
            expected, _ = layout_members(block['members'], block['layout'])
            for want in expected:
                found = members.get(want['name'], {})
                for field, default in (('type', None), ('array', 1), ('row_major', False)):
                    declared = next(m for m in block['members'] if m['name'] == want['name'])
                    if found.get(field, default) != declared.get(field, default):
                        errors.append(block['name'] + '.' + want['name'] + ':REFLECTION_' + field.upper())
                for field in ('offset','array_stride','matrix_stride'):
                    if found.get(field, 0 if field != 'offset' else None) != want[field]: errors.append(block['name'] + '.' + want['name'] + ':REFLECTION_' + field.upper())
    if reflection is not None:
        if 'samplers' not in reflection:
            if manifest['samplers']: errors.append('REFLECTION_SAMPLERS_MISSING')
            reflection = dict(reflection, samplers=[])
        if not isinstance(reflection['samplers'], list): raise ValueError('reflection.samplers must be array')
        if any(not isinstance(s, dict) or not isinstance(s.get('name'), str) for s in reflection['samplers']): raise ValueError('reflection sampler name required')
        if len({s['name'] for s in reflection['samplers']}) != len(reflection['samplers']): raise ValueError('duplicate reflection sampler')
        observed_samplers = {s['name']: s for s in reflection['samplers']}
        for sampler in manifest['samplers']:
            actual = observed_samplers.get(sampler['name'], {})
            for field in ('unit', 'type') + (('location',) if 'location' in sampler else ()):
                if actual.get(field) != sampler[field]: errors.append(sampler['name'] + ':REFLECTION_' + field.upper())
    if baseline is not None:
        if not isinstance(baseline, dict) or any(not isinstance(baseline.get(k), list) for k in ('blocks', 'samplers')): raise ValueError('baseline blocks/samplers required')
        if abi_signature(manifest) != abi_signature(baseline): errors.append('CROSS_VARIANT_ABI_MISMATCH')
    return errors

def abi_signature(manifest):
    # Linked uniform locations can differ without changing the material ABI.
    samplers = [{k: v for k, v in sampler.items() if k != 'location'} for sampler in manifest['samplers']]
    # Declaration order among named blocks/samplers/interfaces is not an ABI.
    # Member order remains meaningful to the layout contract.
    return json.dumps({'blocks': sorted(manifest['blocks'], key=lambda b: b['name']),
                       'samplers': sorted(samplers, key=lambda s: s['name']),
                       'interfaces': sorted(manifest.get('interfaces', []), key=lambda i: i['name'])}, sort_keys=True)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('manifest'); args=parser.parse_args()
    try:
        errors=validate(json.load(open(args.manifest))); print(json.dumps({'errors': errors})); raise SystemExit(bool(errors))
    except (ValueError,OSError) as exc: parser.exit(2,str(exc)+'\n')
