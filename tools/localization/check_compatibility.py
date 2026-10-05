"""Check localization boundaries against the inspected baseline commit.

Also tests that the English audit rejects literal/escaped prose, invalid UTF-8,
and missing translated anchors. Temporary probes are removed after each test.
"""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = sys.argv[1] if len(sys.argv) > 1 else 'e26b5ef378dce617d074822456e734b17c509385'
def original(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)

def source(path):
    return (ROOT / path).read_bytes()

def normalized(data):
    return data.decode('utf-8-sig').replace('\r\n', '\n')

changed = subprocess.check_output(['git', '-c', 'core.safecrlf=false', 'diff', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
checks = 0
def check(condition, label):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(label)

for path in changed:
    if path.endswith(('.cpp', '.cppinc', '.h', '.hpp')) and not path.startswith('SimpleFontHook/ui/'):
        before = re.sub(r'//[^\n]*', '', normalized(original(path)))
        after = re.sub(r'//[^\n]*', '', normalized(source(path)))
        check(before == after, f'non-UI executable source changed: {path}')

immutable = [
    'SimpleFontHook/utils.cpp', 'SimpleFontHook/framework.h',
    'SimpleFontHook/SimpleFontHook.vcxproj',
    'SimpleFontHook/hooks/internal/font_hooks_text_substitution_map.cppinc',
    'SimpleFontHook/hooks/internal/engines/bgi/bgi_compat_state.cppinc',
    'SimpleFontHook/hooks/internal/engines/yuris/yuris_catalog.cppinc',
    'SimpleFontHook/font/font_patcher.cpp',
    'SimpleFontHook/ui/internal/font_picker_font_list.cppinc',
    'SimpleFontHook/ui/internal/font_picker_apply_config.cppinc',
    'LICENSE.txt', 'tools/upx/upx.exe', 'tools/upx/LICENSE', 'tools/upx/COPYING',
]
tracked = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
immutable += [p for p in tracked if 'detours' in p.lower() or p.endswith('.def')]
for path in immutable:
    before, after = original(path), source(path)
    if Path(path).suffix not in {'.exe', '.lib', '.dll'}:
        before, after = normalized(before), normalized(after)
    check(before == after, f'compatibility data or bundled binary changed: {path}')

state_path = 'SimpleFontHook/ui/internal/state/font_picker_state.cppinc'
state_before, state_after = normalized(original(state_path)), normalized(source(state_path))
for array in ('g_charsets', 'g_spoofCharsets', 'g_textSubstitutionModes', 'g_textSubstitutionCodepages', 'g_codepageRedirectPresets'):
    def values(content):
        block = re.search(r'\b' + array + r'\[\]\s*=\s*\{(.*?)\n\};', content, re.S).group(1)
        return re.sub(r'L"(?:\\.|[^"\\])*"', 'LABEL', block)
    check(values(state_before) == values(state_after), f'UI enum or preset values changed: {array}')
for name in ('MIN_WIDTH', 'MIN_HEIGHT', 'UI_SCALE_MIN', 'UI_SCALE_MAX', 'UI_SCALE_STEP',
             'TITLE_HEIGHT', 'SEARCH_HEIGHT', 'CHARSET_HEIGHT', 'SPOOF_HEIGHT', 'TEXTSUB_HEIGHT', 'METRICS_HEIGHT', 'PREVIEW_HEIGHT'):
    pattern = r'\b' + name + r'\s*=\s*([^;]+);'
    check(re.search(pattern, state_before).group(1) == re.search(pattern, state_after).group(1), f'geometry/default changed: {name}')

format_pattern = re.compile(r'%(?:\d+\$)?[-+ #0]*\d*(?:\.\d+)?(?:hh|ll|[hlLjztIw])?[diuoxXfFeEgGaAcCsSpn%]')
for path in changed:
    if path.startswith('SimpleFontHook/ui/') and path.endswith('.cppinc'):
        # Compare the inventory: caption translations may move a formatting call.
        def formats(data, localized=False):
            strings = re.findall(r'(?:L)?"((?:\\.|[^"\\])*)"', normalized(data))
            if localized and path.endswith('font_picker_paint_preview.cppinc'):
                # The new shortcut row adds the already registered hotkey name.
                # Existing translated status placeholders must still match exactly.
                strings.remove('Enter=Apply  Esc=Hide  Hotkey=%s')
            return sorted(tuple(format_pattern.findall(s)) for s in strings if format_pattern.search(s))
        check(formats(original(path)) == formats(source(path), True), f'format placeholders changed: {path}')

probe = ROOT / 'tools/localization/__audit_probe.md'
check(not probe.exists(), 'audit probe path is unused')
for label, payload in (
    ('literal prose', ('# Probe\n' + chr(0x4e2d) + '\n').encode('utf-8')),
    ('escaped prose', ('# Probe\n' + ' '.join(chr(92) + prefix + format(0x4e2d, digits)
                                            for prefix, digits in [('u', '04x'), ('x', '04X'), ('U', '08X')]) + '\n').encode()),
    ('invalid UTF-8', b'# Probe\n\xff\n'),
    ('missing heading', b'# Probe\n[Missing](#missing-anchor)\n'),
):
    try:
        probe.write_bytes(payload)
        result = subprocess.run([sys.executable, str(ROOT / 'tools/localization/check_english.py')], cwd=ROOT, capture_output=True)
        check(result.returncode == 1, f'audit failed to reject {label}')
    finally:
        probe.unlink(missing_ok=True)
print(f'PASS: {checks} compatibility, placeholder, geometry and audit regression checks')
