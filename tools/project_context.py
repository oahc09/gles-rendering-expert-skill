#!/usr/bin/env python3
"""Record the project files, ownership declarations and Git changes for a GLES investigation."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

from gpu_decision_v111 import check_keys, read, require, token


DECLARATIONS = (
    'engine', 'engine_version', 'build_entry', 'backend', 'shader_generation',
    'render_thread_owner', 'resource_owner',
)


def git(root, *arguments):
    return subprocess.run(['git', '-C', str(root), *arguments], check=True,
                          capture_output=True, timeout=30).stdout


def describe(root, manifest):
    root = root.resolve(strict=True)
    check_keys(manifest, ('schema_version', 'project_id', 'source_files', 'allowed_write_files'), DECLARATIONS)
    require(type(manifest['schema_version']) is int and manifest['schema_version'] == 1,
            'unsupported project manifest version')
    require(token(manifest['project_id']), 'invalid project id')
    require(root.samefile(Path(git(root, 'rev-parse', '--show-toplevel').decode('utf-8').rstrip('\r\n'))),
            'project root must be the Git worktree root')
    declared = {name: manifest.get(name) for name in DECLARATIONS}
    for key, value in declared.items():
        require(value is None or (type(value) is str and 0 < len(value) <= 512), f'invalid {key}')
    paths = manifest['source_files']
    allowed = manifest['allowed_write_files']
    require(type(paths) is list and 0 < len(paths) <= 256 and all(type(path) is str for path in paths)
            and len(set(paths)) == len(paths), 'invalid source file list')
    require(type(allowed) is list and all(type(path) is str for path in allowed)
            and len(set(allowed)) == len(allowed) and set(allowed) <= set(paths),
            'write scope must refer to enumerated source files')
    version = git(root, 'rev-parse', 'HEAD', 'HEAD^{tree}').decode('ascii').splitlines()
    status_args = ('status', '--porcelain=v1', '-z', '--untracked-files=all')
    changes = git(root, *status_args)
    sources = []
    resolved = set()
    for name in sorted(paths):
        path = PurePosixPath(name)
        require(not path.is_absolute() and path.as_posix() == name and path.parts
                and '\\' not in name and ':' not in name
                and not any(part.casefold() in {'.git', '..'} for part in path.parts),
                'invalid project-relative source path')
        location = root.joinpath(*path.parts)
        real = location.resolve(strict=True)
        require(real == location and real.is_file() and real not in resolved, 'source must be a unique regular file')
        resolved.add(real)
        before = location.stat()
        with location.open('rb') as source:
            require(os.path.samestat(before, os.fstat(source.fileno())), 'source changed during capture')
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
            after = location.stat()
            require(os.path.samestat(before, after)
                    and (before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                    (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'source changed during capture')
        sources.append({'path': name, 'sha256': digest, 'size': after.st_size})
    require(changes == git(root, *status_args)
            and version == git(root, 'rev-parse', 'HEAD', 'HEAD^{tree}').decode('ascii').splitlines(),
            'project changed during capture')
    return {'schema': 'gles.project-context/v1', 'project_id': manifest['project_id'],
            'source_commit': version[0], 'source_tree': version[1],
            'source_manifest': sources,
            'source_manifest_sha256': hashlib.sha256(
                json.dumps(sources, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest(),
            'worktree_changes_porcelain_v1_z': changes.decode('utf-8', errors='surrogateescape'),
            'allowed_write_files': sorted(allowed),
            'declarations': declared, 'unknown': [name for name in DECLARATIONS if declared[name] is None],
            'observed_backend': None, 'evidence_class': 'SOURCE_SNAPSHOT'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    try:
        context = describe(args.root, read(args.manifest))
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError) as error:
        parser.exit(2, f'{error}\n')
    print(json.dumps(context, indent=2))


if __name__ == '__main__':
    sys.exit(main())
