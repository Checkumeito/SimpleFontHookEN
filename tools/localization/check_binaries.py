"""Compare baseline DLL interfaces, run UPX integrity checks, and match PDB IDs.

Pass the artifact directory containing baseline/win32.dll and baseline/x64.dll.
Only disposable copies are unpacked; standard delivery files stay packed.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DUMPBIN = Path('C:/Program Files (x86)/Microsoft Visual Studio/18/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/dumpbin.exe')
def uint(data, offset):
    return struct.unpack_from('<I', data, offset)[0]

def pdb_identity(path):
    data = path.read_bytes()
    assert data.startswith(b'Microsoft C/C++ MSF 7.00'), 'PDB MSF format'
    size, directory_size, map_block = uint(data, 32), uint(data, 44), uint(data, 52)
    block_count = (directory_size + size - 1) // size
    blocks = struct.unpack_from(f'<{block_count}I', data, map_block * size)
    directory = b''.join(data[b * size:(b + 1) * size] for b in blocks)[:directory_size]
    count = uint(directory, 0)
    sizes = struct.unpack_from(f'<{count}I', directory, 4)
    position = 4 + count * 4
    for index, stream_size in enumerate(sizes):
        count = 0 if stream_size == 0xffffffff else (stream_size + size - 1) // size
        blocks = struct.unpack_from(f'<{count}I', directory, position)
        position += count * 4
        if index == 1:
            info = b''.join(data[b * size:(b + 1) * size] for b in blocks)[:stream_size]
            return info[12:28], uint(info, 8)
    raise AssertionError('missing PDB information stream')

def dll_identity(path):
    data = path.read_bytes()
    pe = uint(data, 0x3c)
    assert data[pe:pe + 4] == b'PE\0\0'
    optional = pe + 24
    sections = struct.unpack_from('<H', data, pe + 6)[0]
    optional_size = struct.unpack_from('<H', data, pe + 20)[0]
    directories = optional + (112 if struct.unpack_from('<H', data, optional)[0] == 0x20b else 96)
    debug_rva, debug_size = struct.unpack_from('<II', data, directories + 6 * 8)
    def offset(rva):
        for i in range(sections):
            section = optional + optional_size + i * 40
            virtual_size, address, raw_size, raw_pointer = struct.unpack_from('<IIII', data, section + 8)
            if address <= rva < address + max(virtual_size, raw_size):
                return raw_pointer + rva - address
        raise AssertionError('unmapped debug RVA')
    start = offset(debug_rva)
    for entry in range(start, start + debug_size, 28):
        if uint(data, entry + 12) == 2:
            raw = uint(data, entry + 24)
            if data[raw:raw + 4] == b'RSDS':
                return data[raw + 4:raw + 20], uint(data, raw + 20)
    raise AssertionError('missing DLL CodeView identity')

def executable_sections(path):
    data = path.read_bytes()
    pe = uint(data, 0x3c)
    count = struct.unpack_from('<H', data, pe + 6)[0]
    start = pe + 24 + struct.unpack_from('<H', data, pe + 20)[0]
    found = {}
    for index in range(count):
        section = start + index * 40
        if uint(data, section + 36) & 0x20000000:
            name = data[section:section + 8].rstrip(b'\0')
            size, pointer = uint(data, section + 16), uint(data, section + 20)
            found[name] = data[pointer:pointer + size]
    return found

def exports(dumpbin, path, log):
    result = subprocess.check_output([str(dumpbin), '/exports', str(path)], text=True)
    log.write_text(result, encoding='utf-8')
    found = []
    for line in result.splitlines():
        match = re.match(r'^\s*(\d+)\s+[0-9a-fA-F]+\s+(?:[0-9A-Fa-f]{8}\s+)?(\S+)(?:\s+\(forwarded to (.*?)\))?$', line)
        if match:
            found.append((int(match[1]), match[2], match[3]))
    assert len(found) == 180, f'expected 180 exports: {path}'
    return found

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--dumpbin', type=Path, default=DEFAULT_DUMPBIN)
    args = parser.parse_args()
    artifacts = args.artifacts.resolve()
    output = artifacts / 'binary-checks'
    output.mkdir(exist_ok=True)
    report = []
    for arch, directory in [('win32', 'Release'), ('x64', 'x64/Release')]:
        dll = ROOT / directory / 'winmm.dll'
        pdb = ROOT / directory / 'winmm.pdb'
        baseline = artifacts / 'baseline' / f'{arch}.dll'
        before = exports(args.dumpbin, baseline, output / f'baseline-exports-{arch}.txt')
        after = exports(args.dumpbin, dll, output / f'localized-exports-{arch}.txt')
        assert before == after, f'export names/ordinals/forwarding targets changed: {arch}'
        integrity = subprocess.check_output([str(ROOT / 'tools/upx/upx.exe'), '-t', str(dll)], text=True)
        (output / f'upx-{arch}.txt').write_text(integrity, encoding='utf-8')
        unpacked = output / f'{arch}-unpacked.dll'
        shutil.copy2(dll, unpacked)
        subprocess.run([str(ROOT / 'tools/upx/upx.exe'), '-d', str(unpacked)], check=True, stdout=subprocess.PIPE)
        # The existing UPX workflow clears CodeView directories. Match the PDB to
        # the retained pre-packing link output, then compare its exported interface.
        linked = artifacts / 'symbols' / arch / 'winmm.dll'
        assert dll_identity(linked) == pdb_identity(pdb), f'DLL/PDB identity mismatch: {arch}'
        assert exports(args.dumpbin, linked, output / f'linked-exports-{arch}.txt') == after
        assert executable_sections(linked) == executable_sections(unpacked), f'packed DLL code differs from linked symbol pair: {arch}'
        item = {'architecture': arch, 'exports': len(after), 'packed_bytes': dll.stat().st_size,
                'unpacked_bytes': unpacked.stat().st_size, 'pdb_bytes': pdb.stat().st_size,
                'pdb_guid_bytes': pdb_identity(pdb)[0].hex(), 'pdb_age': pdb_identity(pdb)[1]}
        report.append(item)
        print(f'PASS {arch}: 180 identical exports; UPX integrity; matching DLL/PDB identity')
    (output / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
