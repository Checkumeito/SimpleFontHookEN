"""Exercise real packed DLLs in disposable native Windows processes.

Build smoke_host.cpp and layout_smoke.cpp for x86/x64 first. Requires Pillow.
Evidence and copied configuration files stay below the supplied artifact directory.
No configuration beside the delivered DLLs is read or written by this harness.
"""
import argparse
import ctypes as c
from ctypes import wintypes as w
import json
import re
from pathlib import Path
import shutil
import subprocess
import time
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
u = c.WinDLL('user32', use_last_error=True)
g = c.WinDLL('gdi32', use_last_error=True)
CALLBACK = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
def bind(dll, name, args, result):
    fn = getattr(dll, name)
    fn.argtypes, fn.restype = args, result
    return fn
enum = bind(u, 'EnumWindows', [CALLBACK, w.LPARAM], w.BOOL)
enum_child = bind(u, 'EnumChildWindows', [w.HWND, CALLBACK, w.LPARAM], w.BOOL)
pid_of = bind(u, 'GetWindowThreadProcessId', [w.HWND, c.POINTER(w.DWORD)], w.DWORD)
class_of = bind(u, 'GetClassNameW', [w.HWND, w.LPWSTR, c.c_int], c.c_int)
send = bind(u, 'SendMessageTimeoutW', [w.HWND, w.UINT, w.WPARAM, w.LPARAM, w.UINT, w.UINT, c.POINTER(c.c_size_t)], w.LPARAM)
post = bind(u, 'PostMessageW', [w.HWND, w.UINT, w.WPARAM, w.LPARAM], w.BOOL)
rect_of = bind(u, 'GetClientRect', [w.HWND, c.POINTER(w.RECT)], w.BOOL)
move = bind(u, 'SetWindowPos', [w.HWND, w.HWND, c.c_int, c.c_int, c.c_int, c.c_int, w.UINT], w.BOOL)
visible = bind(u, 'IsWindowVisible', [w.HWND], w.BOOL)
valid = bind(u, 'IsWindow', [w.HWND], w.BOOL)
client_to_screen = bind(u, 'ClientToScreen', [w.HWND, c.POINTER(w.POINT)], w.BOOL)
set_cursor = bind(u, 'SetCursorPos', [c.c_int, c.c_int], w.BOOL)
get_cursor = bind(u, 'GetCursorPos', [c.POINTER(w.POINT)], w.BOOL)
get_dc = bind(u, 'GetDC', [w.HWND], w.HDC)
release_dc = bind(u, 'ReleaseDC', [w.HWND, w.HDC], c.c_int)
create_dc = bind(g, 'CreateCompatibleDC', [w.HDC], w.HDC)
create_bitmap = bind(g, 'CreateCompatibleBitmap', [w.HDC, c.c_int, c.c_int], w.HBITMAP)
select = bind(g, 'SelectObject', [w.HDC, w.HGDIOBJ], w.HGDIOBJ)
delete_object = bind(g, 'DeleteObject', [w.HGDIOBJ], w.BOOL)
delete_dc = bind(g, 'DeleteDC', [w.HDC], w.BOOL)
print_window = bind(u, 'PrintWindow', [w.HWND, w.HDC, w.UINT], w.BOOL)
class Header(c.Structure):
    _fields_ = [('size', w.DWORD), ('width', w.LONG), ('height', w.LONG),
                ('planes', w.WORD), ('bits', w.WORD), ('compression', w.DWORD),
                ('image_size', w.DWORD), ('x', w.LONG), ('y', w.LONG),
                ('used', w.DWORD), ('important', w.DWORD)]
get_bits = bind(g, 'GetDIBits', [w.HDC, w.HBITMAP, w.UINT, w.UINT, c.c_void_p, c.POINTER(Header), w.UINT], c.c_int)

def message(hwnd, msg, wp=0, lp=0):
    result = c.c_size_t()
    if not send(hwnd, msg, wp, lp, 2, 10000, c.byref(result)):
        raise AssertionError(f'window message timed out: {msg:#x}')
    return result.value

def text(hwnd, value):
    buffer = c.create_unicode_buffer(value)
    message(hwnd, 0x000c, 0, c.addressof(buffer))

def windows(pid, parent=None):
    found = {}
    @CALLBACK
    def visit(hwnd, _):
        actual = w.DWORD()
        pid_of(hwnd, c.byref(actual))
        if actual.value == pid:
            name = c.create_unicode_buffer(128)
            class_of(hwnd, name, 128)
            found.setdefault(name.value, []).append(hwnd)
        return True
    (enum_child(parent, visit, 0) if parent else enum(visit, 0))
    return found

def wait_for(predicate, label, seconds=15):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError(f'timed out: {label}')

def capture(hwnd, path):
    rect = w.RECT()
    rect_of(hwnd, c.byref(rect))
    width, height = rect.right, rect.bottom
    dc = get_dc(hwnd)
    memory = create_dc(dc)
    bitmap = create_bitmap(dc, width, height)
    old = select(memory, bitmap)
    try:
        assert print_window(hwnd, memory, 2), 'PrintWindow'
        select(memory, old)
        info = Header(c.sizeof(Header), width, -height, 1, 32, 0, 0, 0, 0, 0, 0)
        pixels = c.create_string_buffer(width * height * 4)
        assert get_bits(dc, bitmap, 0, height, pixels, c.byref(info), 0) == height
        image = Image.frombytes('RGB', (width, height), pixels.raw, 'raw', 'BGRX')
        assert image.getextrema()[0][1] > 0, 'nonblank capture'
        image.save(path)
        return image
    finally:
        select(memory, old)
        delete_object(bitmap)
        delete_dc(memory)
        release_dc(hwnd, dc)

def click(hwnd, x, y):
    lp = x | (y << 16)
    message(hwnd, 0x0201, 1, lp)
    message(hwnd, 0x0202, 0, lp)
    time.sleep(0.04)

def wheel(hwnd, x, y, notches):
    point = w.POINT(x, y)
    client_to_screen(hwnd, c.byref(point))
    set_cursor(point.x, point.y)
    for _ in range(abs(notches)):
        message(hwnd, 0x020a, ((120 if notches > 0 else -120) & 0xffff) << 16)
    time.sleep(0.05)

def read_ini(path):
    return dict(line.split('=', 1) for line in path.read_text(encoding='utf-8-sig').splitlines()
                if '=' in line and not line.startswith((';', '#')))

def exercise(arch, artifacts):
    case = artifacts / f'native-{arch}'
    case.mkdir(exist_ok=True)
    images = case / 'screenshots'
    images.mkdir(exist_ok=True)
    # Unique case directories make reruns preserve previous evidence.
    dll = ROOT / ('Release' if arch == 'x86' else 'x64/Release') / 'winmm.dll'
    copied = case / 'winmm.dll'
    shutil.copy2(dll, copied)
    ini = case / 'FontHook.ini'
    assert not ini.exists(), 'use a fresh artifact directory for each run'
    rows = {}
    output = subprocess.check_output([str(artifacts / f'layout-smoke-{arch}.exe'), 'dump'], text=True)
    for line in output.splitlines():
        if line.startswith('ROW '):
            fields = line.split()
            rows[(fields[1], *map(int, fields[2:6]))] = tuple(map(int, fields[6:10]))
    log_path = case / 'host.log'
    checks = []
    def check(condition, label):
        assert condition, label
        checks.append(label)
    log = log_path.open('w', encoding='utf-8')
    proc = subprocess.Popen([str(artifacts / f'smoke-host-{arch}.exe'), str(copied)],
                            cwd=case, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    picker = host = None
    def shot(name):
        time.sleep(0.1)
        return capture(picker, images / f'{name}.png')
    def config_is(key, value):
        return wait_for(lambda: ini.exists() and read_ini(ini).get(key) == str(value), key)
    def row_click(index, active, mode, preset, scale='1.0', edge=False):
        left, top, right, bottom = rows[(scale, active, mode, preset, index)]
        click(picker, right - 1 if edge else left, bottom - 1 if edge else top)
    def zoom(scale):
        # Saturate at the existing minimum, then take the existing 0.1 steps.
        for _ in range(12): click(picker, 330, 24)
        for _ in range(round((scale - 0.7) * 10)): click(picker, 366, 24)
    def edit_metric(x, y, value):
        before = set(windows(proc.pid, picker).get('Edit', []))
        click(picker, x, y)
        edit = wait_for(lambda: next(iter(set(windows(proc.pid, picker).get('Edit', [])) - before), None), 'metric edit')
        text(edit, value)
        message(edit, 0x0100, 13)
        wait_for(lambda: not valid(edit), 'metric commit')
    try:
        found = wait_for(lambda: windows(proc.pid).get('FontPickerOverlay'), 'picker startup')
        picker = found[0]
        host = windows(proc.pid)['SimpleFontHookENSmokeHost'][0]
        wait_for(lambda: visible(picker), 'visible first startup')
        time.sleep(0.5)
        rect = w.RECT(); rect_of(picker, c.byref(rect))
        check((rect.right, rect.bottom) == (480, 720), 'default client size 480x720')
        shot('startup-default')
        search = windows(proc.pid, picker)['Edit'][0]
        text(search, 'Segoe UI')
        message(picker, 0x0100, 13)
        config_is('FontNameW', 'Segoe UI')
        config_is('EnableFontHook', 1)
        wait_for(lambda: 'face=Segoe UI' in log_path.read_text(errors='replace'), 'hooked font application')
        check(True, 'search/application persists font and changes native GDI result')
        text(search, '')
        for height in (640, 720):
            move(picker, None, 50, 50, 480, height, 0x0014)
            for scale in (0.7, 1.0, 1.8):
                zoom(scale)
                shot(f'fonts-{height}-{scale:.1f}')
        move(picker, None, 50, 50, 480, 640, 0x0014)
        zoom(1.8)
        first = shot('one-row-before')
        wheel(picker, 220, 250, -1)
        after = shot('one-row-after')
        check(first.crop((0, 208, 480, 335)).tobytes() != after.crop((0, 208, 480, 335)).tobytes(), 'one-row font list scroll at maximum zoom')
        before_charset = shot('charset-before')
        wheel(picker, 220, 112, -12)
        after_charset = shot('charset-after')
        check(before_charset.crop((0, 98, 480, 134)).tobytes() != after_charset.crop((0, 98, 480, 134)).tobytes(), 'charset horizontal scrolling')
        click(picker, 390, 115)
        shot('charset-selected')
        zoom(1.0)
        # Edge clicks exercise the real DLL using production geometry.
        row_click(0, 0, 0, 0)
        config_is('EnableTextSubstitution', 1)
        wait_for(lambda: re.search(r'MAPPING count=3 codepoints=4e24,', log_path.read_text(errors='replace')), 'native JP proxy mapping')
        for mode in (1, 2, 0):
            offset = log_path.stat().st_size
            row_click(1, 1, (mode - 1) % 3, 0, edge=True)
            config_is('TextSubstitutionMode', mode)
            expected = {0: r'MAPPING count=3 codepoints=4e24,',
                        1: r'MAPPING count=3 codepoints=4e21,4e24,4e24',
                        2: r'MAPPING count=3 codepoints=4e21,5169,5169'}[mode]
            wait_for(lambda: re.search(expected, log_path.read_bytes()[offset:].decode(errors='replace')), 'native mapping mode')
        check(True, 'native decoded text follows all three mapping tables')
        row_click(2, 1, 0, 0, edge=True)
        config_is('EnableCodepageRedirect', 1)
        wait_for(lambda: 'cp932_count=1 first=3042' in log_path.read_text(errors='replace'), 'native redirected conversion')
        check(True, 'native CP932 request redirects UTF-8 input correctly')
        presets = [(932, 65001), (936, 65001), (0, 65001), (65001, 932), (65001, 936)]
        for previous, current in zip(range(5), (1, 2, 3, 4, 0)):
            row_click(3, 3, 0, previous, edge=True)
            config_is('CodepageRedirectFrom', presets[current][0])
            config_is('CodepageRedirectTo', presets[current][1])
        row_click(2, 3, 0, 0)
        config_is('EnableCodepageRedirect', 0)
        row_click(0, 1, 0, 0, edge=True)
        config_is('EnableTextSubstitution', 0)
        check(True, 'all mapping modes and five redirect presets persist at button edges')
        click(picker, 10, 143)
        config_is('EnableCodepageSpoof', 1)
        for target in (134, 136, 1, 129, 128):
            click(picker, 135, 143)
            config_is('SpoofToCharset', target)
        click(picker, 10, 143)
        config_is('EnableCodepageSpoof', 0)
        check(True, 'spoof toggle and all five target charsets persist')
        # Restore Default charset and a known installed font before metric tests.
        wheel(picker, 220, 112, 12)
        click(picker, 25, 112)
        text(search, 'Segoe UI'); message(picker, 0x0100, 13)
        for x, y, value, key, expected in (
            (109, 355, '2.00', 'FontWidthScale1000', 2000),
            (268, 355, '0.50', 'FontHeightScale1000', 500),
            (427, 355, '60', 'FontCharSpacing', 60),
            (109, 386, '2000', 'FontAscentPermille', 2000),
            (268, 386, '-2000', 'FontDescentPermille', -2000),
            (427, 386, '-80', 'FontLineSpacing', -80),
            (109, 417, '900', 'FontWeight', 900),
        ):
            edit_metric(x, y, value)
            config_is(key, expected)
        zoom(1.8); shot('metric-extremes-1.8')
        zoom(0.7); shot('metric-extremes-0.7')
        zoom(1.0)
        click(picker, 180, 406)  # Set Ref
        click(picker, 330, 406)  # Match Ref
        shot('matched-reference')
        click(picker, 330, 437)  # Reset
        for key in ('EnableFontHeightScale', 'EnableFontWidthScale', 'EnableFontCharSpacing', 'EnableFontVerticalMetrics', 'EnableFontLineSpacing', 'EnableFontWeight'):
            config_is(key, 0)
        check(True, 'all metric edits at numeric extremes, reference matching and reset')
        message(picker, 0x0100, 9)
        for height in (640, 720):
            move(picker, None, 50, 50, 480, height, 0x0014)
            for scale in (0.7, 1.0, 1.8):
                zoom(scale)
                for section in range(4):
                    click(picker, 25 + section * 116, 130)
                    shot(f'guide-{height}-{scale:.1f}-{section}-top')
                    wheel(picker, 220, 400, -100)
                    shot(f'guide-{height}-{scale:.1f}-{section}-bottom')
        check(True, 'all four guide sections wrap and scroll across six viewport/zoom combinations')
        message(picker, 0x0100, 27)
        wait_for(lambda: not visible(picker), 'Escape hides')
        message(picker, 0x0312, 1)
        wait_for(lambda: visible(picker), 'hotkey restores')
        time.sleep(0.4)
        check(True, 'Escape and hotkey hide/restore')
        click(picker, 410, 24)
        check(bind(u, 'IsIconic', [w.HWND], w.BOOL)(picker), 'native minimize')
        message(picker, 0x0312, 1)
        wait_for(lambda: not bind(u, 'IsIconic', [w.HWND], w.BOOL)(picker), 'hotkey restores minimized picker')
        # Destroy the picker with an active metric control to exercise owned-font cleanup.
        message(picker, 0x0100, 9)
        zoom(1.0)
        move(picker, None, 50, 50, 480, 640, 0x0014)
        click(picker, 109, 355)
        message(picker, 0x0010)
        wait_for(lambda: not valid(picker), 'picker shutdown')
        post(host, 0x0010, 0, 0)
        proc.wait(timeout=10)
        check(proc.returncode == 0, 'native shutdown with active metric edit')
    finally:
        if proc.poll() is None:
            if host: post(host, 0x0010, 0, 0)
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.terminate(); proc.wait(timeout=5)
        log.close()
    # Restart the same copied DLL with its saved INI, hidden startup, and large raw
    # height/width values. These values must remain unchanged by presentation fitting.
    saved = read_ini(ini)
    saved.update(PickerShowOnStartup='0', EnableFontHeightScale='1', FontHeightScale1000='1000000',
                 EnableFontWidthScale='1', FontWidthScale1000='1000000')
    ini.write_text('[FontHook]\n' + '\n'.join(f'{k}={v}' for k, v in saved.items()) + '\n', encoding='utf-8-sig')
    with (case / 'restored-host.log').open('w', encoding='utf-8') as restored_log:
        proc = subprocess.Popen([str(artifacts / f'smoke-host-{arch}.exe'), str(copied)], cwd=case,
                                stdout=restored_log, stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        host = None
        try:
            picker = wait_for(lambda: windows(proc.pid).get('FontPickerOverlay'), 'restored picker')[0]
            host = windows(proc.pid)['SimpleFontHookENSmokeHost'][0]
            time.sleep(0.6)
            check(not visible(picker), 'saved hidden-startup configuration restored')
            message(picker, 0x0312, 1)
            wait_for(lambda: visible(picker), 'restored hotkey')
            time.sleep(0.5)
            shot('restored-large-ini')
            check(read_ini(ini)['FontHeightScale1000'] == '1000000', 'preview fitting preserves raw configuration')
            message(picker, 0x0010)
            post(host, 0x0010, 0, 0)
            proc.wait(timeout=10)
            check(proc.returncode == 0, 'restored native shutdown')
        finally:
            if proc.poll() is None:
                if host: post(host, 0x0010, 0, 0)
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.terminate(); proc.wait(timeout=5)
    (case / 'results.json').write_text(json.dumps({'architecture': arch, 'checks': checks,
        'screenshots': len(list(images.glob('*.png')))}, indent=2), encoding='utf-8')
    print(f'PASS {arch}: {len(checks)} native scenario checks; {len(list(images.glob("*.png")))} screenshots')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--arch', choices=('x86', 'x64', 'both'), default='both')
    args = parser.parse_args()
    bind(u, 'SetProcessDPIAware', [], w.BOOL)()
    original_cursor = w.POINT(); get_cursor(c.byref(original_cursor))
    try:
        for architecture in ('x86', 'x64') if args.arch == 'both' else (args.arch,):
            exercise(architecture, args.artifacts.resolve())
    finally:
        set_cursor(original_cursor.x, original_cursor.y)
