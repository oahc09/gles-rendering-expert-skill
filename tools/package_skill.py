#!/usr/bin/env python3
"""Build a reproducible local candidate archive and install it into a new directory."""

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from zipfile import BadZipFile, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
INDEX = 'skill-package-manifest.json'
CANDIDATE_VERSION = '1.1.3'
PLAN = 'docs/GLES_Rendering_Expert_Skill_v1.1.3_Development_Plan_2026-11-28.md'
CANDIDATE_FILES = {
    PLAN, 'docs/v1.1.3/README.md', 'docs/v1.1.3/obligations.json', 'docs/v1.1.3/wallpaper-project.json',
    'docs/v1.1.3/discard-workload.json',
    'docs/v1.1.3/execution-status.md',
    'docs/v1.1.3/routing-history.md', 'docs/v1.1.3/mesa-linux.json',
    'tools/check_v113_acceptance.py', 'tools/gpu_session.py', 'tools/package_skill.py', 'tools/project_context.py',
    'tools/test_gpu_session.py',
    'benchmarks/attachment_controls/discard.py',
    'benchmarks/workflow/strategies.py', 'benchmarks/workflow/strategy_render.py',
    'tools/experience_cases.py',
    'examples/engine_cases/godot-g03/.gitignore', 'examples/engine_cases/godot-g03/README.md',
    'examples/engine_cases/godot-g03/project.godot', 'examples/engine_cases/godot-g03/battle.tscn',
    'examples/engine_cases/godot-g03/battle.gd',
    'examples/engine_cases/filament-g06/.gitignore', 'examples/engine_cases/filament-g06/README.md',
    'examples/engine_cases/filament-g06/build.gradle', 'examples/engine_cases/filament-g06/settings.gradle',
    'examples/engine_cases/filament-g06/gradle.properties', 'examples/engine_cases/filament-g06/gradle.lockfile',
    'examples/engine_cases/filament-g06/check_readbacks.py',
    'examples/engine_cases/filament-g06/src/main/AndroidManifest.xml',
    'examples/engine_cases/filament-g06/src/main/assets/amber.gltf',
    'examples/engine_cases/filament-g06/src/main/assets/blue.gltf',
    'examples/engine_cases/filament-g06/src/main/java/org/example/gleslab/filament/ViewerActivity.java',
}


def path_for(root, name):
    path = PurePosixPath(name)
    if (not path.parts or path.is_absolute() or path.as_posix() != name or
            any(part.casefold() in {'..', '.git'} or part.endswith(('.', ' ')) or
                re.search(r'[\x00-\x1f\\:*?"<>|]', part) or
                re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part, re.I)
                for part in path.parts)):
        raise ValueError(f'invalid archive path {name!r}')
    return root.joinpath(*path.parts)


def digest(data):
    return {'size': len(data), 'sha256': sha256(data).hexdigest()}


def write(archive, name, data):
    info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def build(path):
    tracked = subprocess.check_output(['git', 'ls-files', '--cached', '-z'], cwd=ROOT).decode('utf-8')
    names = set(tracked.rstrip('\0').split('\0')) | CANDIDATE_FILES
    if INDEX in names or len({name.casefold() for name in names}) != len(names):
        raise ValueError('duplicate package path')
    version = re.search(r'^  version: (\S+)$', (ROOT / 'SKILL.md').read_text(encoding='utf-8'), re.M).group(1)
    files = {}
    manifest = {'schema_version': 1, 'candidate': CANDIDATE_VERSION, 'skill_version': version,
                'files': files}
    with ZipFile(path, 'x') as archive:
        for name in sorted(names):
            source = path_for(ROOT, name)
            if source.resolve(strict=True) != source or not source.is_file():
                raise ValueError(f'expected a regular source file: {name}')
            data = source.read_bytes()
            files[name] = digest(data)
            write(archive, name, data)
        write(archive, INDEX, (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())
    with path.open('rb') as stream:
        return {'archive': str(path), 'sha256': sha256_stream(stream), **identity(manifest)}


def identity(manifest):
    return {'candidate': manifest['candidate'], 'skill_version': manifest['skill_version'],
            'files': len(manifest['files'])}


def sha256_stream(stream):
    hash_value = sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        hash_value.update(block)
    return hash_value.hexdigest()


def install(path, target):
    with ZipFile(path) as archive:
        manifest_bytes = archive.read(INDEX)
        manifest = json.loads(manifest_bytes)
        files = manifest['files']
        listed = archive.namelist()
        expected = set(files) | {INDEX}
        if (manifest['schema_version'] != 1 or INDEX in files or
                not {'SKILL.md', 'LICENSE'} <= expected or set(listed) != expected or
                len({name.casefold() for name in listed}) != len(listed)):
            raise ValueError('package contents differ from manifest')
        for name, fingerprint in files.items():
            path_for(target, name)
            if archive.getinfo(name).file_size != fingerprint['size']:
                raise ValueError(f'package size mismatch: {name}')
            with archive.open(name) as data:
                if sha256_stream(data) != fingerprint['sha256']:
                    raise ValueError(f'package hash mismatch: {name}')
        target.mkdir()
        for name in sorted(expected):
            output = path_for(target, name)
            output.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, output.open('xb') as stream:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    stream.write(block)
    return {'installed': str(target), **identity(manifest)}


def check_installation(root):
    root = root.resolve(strict=True)
    manifest = json.loads((root / INDEX).read_text(encoding='utf-8'))
    files = manifest['files']
    if (manifest['schema_version'] != 1 or INDEX in files or
            not {'SKILL.md', 'LICENSE'} <= files.keys() or
            len({name.casefold() for name in files}) != len(files)):
        raise ValueError('invalid package manifest')
    for name, fingerprint in files.items():
        path = path_for(root, name)
        if path.resolve(strict=True) != path or not path.is_file():
            raise ValueError(f'installed path is not a regular file: {name}')
        if path.stat().st_size != fingerprint['size']:
            raise ValueError(f'installed file size mismatch: {name}')
        with path.open('rb') as stream:
            if sha256_stream(stream) != fingerprint['sha256']:
                raise ValueError(f'installed file hash mismatch: {name}')
    return {'status': 'PACKAGE_VERIFIED', **identity(manifest)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest='command', required=True)
    subcommands.add_parser('build').add_argument('archive', type=Path)
    installer = subcommands.add_parser('install')
    installer.add_argument('archive', type=Path)
    installer.add_argument('new_directory', type=Path)
    subcommands.add_parser('check').add_argument('installed_directory', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'build':
            result = build(args.archive)
        elif args.command == 'install':
            result = install(args.archive, args.new_directory)
        else:
            result = check_installation(args.installed_directory)
    except (OSError, ValueError, KeyError, BadZipFile, subprocess.SubprocessError) as error:
        parser.exit(2, f'{error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    sys.exit(main())
