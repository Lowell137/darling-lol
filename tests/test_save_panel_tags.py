"""Offline contracts for NSSavePanel's unsupported Finder-tag compatibility."""
import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = 'AppKit/NSSavePanel.subproj/NSSavePanel.m'
HEADER = 'AppKit/include/AppKit/NSSavePanel.h'
PROBE_SOURCE = 'tools/riot-save-panel-tag-check.m'
BUILD_HELPER = 'tools/build-riot-save-panel-tag-check.py'


def added_source(path):
    marker = f'diff --git a/{path} b/{path}\n'
    section = (ROOT / 'patches/cocotron.patch').read_text().split(marker, 1)[1]
    section = section.split('\ndiff --git ', 1)[0]
    return '\n'.join(line[1:] for line in section.splitlines()
                     if line.startswith('+') and not line.startswith('+++'))


def extract_patch(path):
    marker = f'diff --git a/{path} b/{path}\n'
    patch_text = (ROOT / 'patches/cocotron.patch').read_text()
    if marker not in patch_text:
        raise AssertionError(f'Missing patch section for {path}')
    section = patch_text.split(marker, 1)[1].split('\ndiff --git ', 1)[0]
    return marker + section + '\n'


def method(source, signature):
    match = re.search(re.escape(signature) + r'\s*\{([^}]+)\}', source)
    if match is None:
        raise AssertionError(f'Missing implementation: {signature}')
    return match.group(1)


class SavePanelTagTests(unittest.TestCase):
    def test_tag_names_setter_accepts_unsupported_metadata_without_storing_it(self):
        body = method(added_source(IMPLEMENTATION), '- (void) setTagNames: (NSArray *) names')
        self.assertIn('(void)names;', body)
        self.assertNotIn('retain', body)
        self.assertNotIn('copy', body)

    def test_tag_names_getter_returns_an_empty_array_not_nil(self):
        body = method(added_source(IMPLEMENTATION), '- (NSArray *) tagNames')
        self.assertIn('return [NSArray array];', body)

    def test_public_header_declares_both_tag_name_methods(self):
        header = added_source(HEADER)
        self.assertIn('- (void) setTagNames: (NSArray *) names;', header)
        self.assertIn('- (NSArray *) tagNames;', header)

    def test_existing_tag_field_and_modal_fixes_are_retained(self):
        source = added_source(IMPLEMENTATION)
        self.assertIn('- (void) setShowsTagField: (BOOL) flag', source)
        self.assertIn('- (BOOL) showsTagField', source)
        self.assertIn('- (void) _dismissWithCode: (NSModalResponse) code', source)
        self.assertNotIn('setShowsTags:', source)

    def test_patch_applies_cleanly_to_pinned_upstream_cocotron(self):
        if not shutil.which('patch'):
            self.skipTest('patch executable required')
        manifest = json.loads((ROOT / 'upstream/manifest.json').read_text())
        component = next(c for c in manifest['components'] if c['patch'] == 'patches/cocotron.patch')
        repo = ROOT / 'build/darling-src' / component['path']
        if not (repo / '.git').exists():
            self.skipTest('prepared Darling sources required')

        revision = component['revision']
        for relpath in [IMPLEMENTATION, HEADER]:
            filename = Path(relpath).name
            original = subprocess.check_output(['git', '-C', str(repo), 'show', f'{revision}:{relpath}'])
            with tempfile.TemporaryDirectory() as td:
                work_file = Path(td) / filename
                work_file.write_bytes(original)
                patch_file = Path(td) / f'{filename}.patch'
                patch_file.write_text(extract_patch(relpath))
                res = subprocess.run(
                    ['patch', '--dry-run', '--fuzz=0', str(work_file), str(patch_file)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(res.returncode, 0, f'Patch failed to apply to {relpath}: {res.stderr}\n{res.stdout}')

    def test_extracted_method_bodies_compile_with_clang(self):
        clang = shutil.which('clang')
        if not clang:
            self.skipTest('clang not available')
        impl = added_source(IMPLEMENTATION)
        setter_body = method(impl, '- (void) setTagNames: (NSArray *) names')
        getter_body = method(impl, '- (NSArray *) tagNames')
        snippet = f'''
@interface NSObject
+ (instancetype)alloc;
- (instancetype)init;
@end

@interface NSArray : NSObject
+ (instancetype)array;
@end

@interface NSSavePanel : NSObject
- (void) setTagNames: (NSArray *) names;
- (NSArray *) tagNames;
@end

@implementation NSSavePanel
- (void) setTagNames: (NSArray *) names {{{setter_body}}}
- (NSArray *) tagNames {{{getter_body}}}
@end
'''
        with tempfile.NamedTemporaryFile(suffix='.m', mode='w') as f:
            f.write(snippet)
            f.flush()
            res = subprocess.run(
                [clang, '-Qunused-arguments', '-x', 'objective-c', '-fsyntax-only', '-Werror', f.name],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, f'Clang syntax check failed: {res.stderr}')

    def test_builder_compiles_and_links_probe_without_embedding_shim(self):
        source = ROOT / BUILD_HELPER
        self.assertTrue(source.exists(), f'Missing build helper: {BUILD_HELPER}')
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            driver = project / 'tools' / source.name
            driver.parent.mkdir()
            driver.write_text(source.read_text())
            framework = project / 'build/darling-src/build/src/external/cocotron/AppKit'
            cmake = framework / 'CMakeFiles/X11_backend.dir'
            cmake.mkdir(parents=True)
            (cmake / 'flags.make').write_text('C_DEFINES = -DTEST\nC_INCLUDES = -Itest\nC_FLAGS = -O0\n')
            calls = []
            with patch('subprocess.run', side_effect=lambda argv, **kw: calls.append((argv, kw))):
                runpy.run_path(str(driver), run_name='__main__')
            probe_name = 'riot-save-panel-tag-check'
            compiles = [argv for argv, _ in calls if str(project / f'tools/{probe_name}.m') in argv]
            self.assertEqual(len(compiles), 1, 'probe must be compiled')
            self.assertEqual(compiles[0][compiles[0].index('-o') + 1], str(project / f'build/{probe_name}.o'))
            links = [argv for argv, _ in calls if str(project / f'build/{probe_name}') in argv]
            self.assertEqual(len(links), 1, 'probe must be linked')
            self.assertIn(str(project / f'build/{probe_name}.o'), links[0])
            self.assertIn('AppKit', links[0])
            for argv, _ in calls:
                for arg in argv:
                    self.assertNotIn('compat', arg)

    def test_probe_declares_only_and_implements_no_shim(self):
        source = (ROOT / PROBE_SOURCE).read_text()
        self.assertIn('@interface NSSavePanel (RiotTagProbeDeclarations)', source)
        self.assertIn('- (void)setTagNames:(NSArray *)names;', source)
        self.assertIn('- (NSArray *)tagNames;', source)
        self.assertIn('- (void)setShowsTagField:(BOOL)value;', source)
        self.assertIn('- (BOOL)showsTagField;', source)
        self.assertNotIn('@implementation NSSavePanel', source, 'probe must not contain compatibility shim')
        self.assertIn('checkPanel([NSSavePanel class])', source)
        self.assertIn('checkPanel([NSOpenPanel class])', source)


if __name__ == '__main__':
    unittest.main()
