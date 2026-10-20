#!/usr/bin/env python3
"""Build the standalone NSSavePanel Finder-tag compatibility check."""
from pathlib import Path
import json
import shlex
import subprocess

root = Path(__file__).resolve().parent.parent
folder = root / 'build/darling-src/build/src/external/cocotron/AppKit'
config = root / 'build/config.json'
sdk = json.loads(config.read_text())['sdk'] if config.exists() else '/usr/local/libexec/darling'
flags = {}
for line in (folder / 'CMakeFiles/X11_backend.dir/flags.make').read_text().splitlines():
    if line.startswith('C_') and ' = ' in line:
        key, value = line.split(' = ', 1)
        flags[key] = shlex.split(value)
obj = root / 'build/riot-save-panel-tag-check.o'
subprocess.run(['clang', *flags['C_DEFINES'], *flags['C_INCLUDES'], *flags['C_FLAGS'],
                '-O2', '-fblocks', '-UNDEBUG', '-Wno-macro-redefined', '-c', str(root / 'tools/riot-save-panel-tag-check.m'),
                '-o', str(obj)], check=True)
subprocess.run(['clang', '-target', 'x86_64-apple-macosx11.0', '-fuse-ld=lld', '-nostdlib',
                '-isysroot', sdk, str(obj), '-lSystem', '-lobjc',
                '-framework', 'AppKit', '-framework', 'CoreFoundation', '-framework', 'Foundation',
                '-o', str(root / 'build/riot-save-panel-tag-check')], check=True)
