"""Audit tracked and non-ignored source text, including escaped Unicode literals.

Run from any directory: python tools/localization/check_english.py
The compatibility allowlist is deliberately limited to exact file/literal pairs.
"""
from pathlib import Path
import json
import re
import subprocess
import sys
from urllib.parse import unquote

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]
RULES = json.loads((Path(__file__).with_name('compatibility_literals.json')).read_text(encoding='utf-8'))
CJK = re.compile(r'[\u3000-\u303f\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\uff01-\uff60]')
ESCAPES = re.compile(r'\\(?:x([0-9a-fA-F]+)|u([0-9a-fA-F]{4})|U([0-9a-fA-F]{8}))')
TEXT_SUFFIXES = {'.md', '.cpp', '.cppinc', '.h', '.hpp', '.bat', '.py', '.json', '.txt', '.sln', '.vcxproj', '.user', '.filters', '.rc', '.ps1', '.sh', '.yml', '.yaml', '.cmake'}

def decode_escapes(text):
    def replace(match):
        value = int(next(part for part in match.groups() if part), 16)
        return chr(value) if value <= 0x10ffff else match.group(0)
    return ESCAPES.sub(replace, text)

def anchors(text):
    found = set()
    counts = {}
    in_fence = False
    for line in text.splitlines():
        if line.startswith('```'):
            in_fence = not in_fence
        if in_fence:
            continue
        match = re.match(r'^#{1,6}\s+(.+)', line)
        if match:
            slug = re.sub(r'[^\w\- ]', '', match[1].lower()).replace(' ', '-')
            count = counts.get(slug, 0)
            found.add(slug + (f'-{count}' if count else ''))
            counts[slug] = count + 1
    return found

paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
errors = []
checked = 0
allowed_lines = 0
for relative in sorted(set(paths) - {''}):
    path = ROOT / relative
    if path.suffix not in TEXT_SUFFIXES and path.name not in {'LICENSE', 'COPYING'}:
        continue
    try:
        content = path.read_bytes().decode('utf-8-sig')
    except UnicodeDecodeError:
        errors.append(f'{relative}: not valid UTF-8')
        continue
    checked += 1
    rule = RULES.get(relative, {})
    if rule.get('whole_file'):
        # This one immutable mapping table consists of actual character pairs.
        continue
    for number, line in enumerate(content.splitlines(), 1):
        decoded = decode_escapes(line)
        if relative == 'tools/localization/check_english.py':
            decoded = decoded.replace(decode_escapes(CJK.pattern), '')
        if relative == 'tools/localization/compatibility_literals.json':
            # The metadata's exact literal keys are compatibility data themselves.
            for entry in RULES.values():
                for literal in entry.get('literals', {}):
                    decoded = decoded.replace(literal, '')
        for literal in rule.get('literals', {}):
            decoded = decoded.replace(literal, '')
        if CJK.search(decoded):
            errors.append(f'{relative}:{number}: unreviewed non-English text: {line.strip()[:180]}')
        elif CJK.search(decode_escapes(line)):
            allowed_lines += 1
    if path.suffix == '.md':
        if content.count('```') % 2:
            errors.append(f'{relative}: unbalanced code fences')
        for target in re.findall(r'(?<!!)\[[^\]]*\]\(([^)]+)\)', content):
            if re.match(r'^[a-z]+:', target, re.I):
                continue
            filename, _, fragment = unquote(target).partition('#')
            destination = path.parent / filename if filename else path
            if not destination.exists():
                errors.append(f'{relative}: missing link target {target}')
            elif fragment and destination.is_file() and destination.suffix == '.md':
                if fragment not in anchors(destination.read_text(encoding='utf-8-sig')):
                    errors.append(f'{relative}: missing heading anchor {target}')

print(f'English audit: {checked} text files; {allowed_lines} reviewed literal lines; {len(errors)} errors')
for error in errors:
    print(error)
sys.exit(bool(errors))
