import re
import json
from pathlib import Path

root = Path('.')
docs_dir = root / 'docs'
map_base = {}
for p in docs_dir.glob('*.md'):
    m = re.match(r'^(\d{8})-(.+)$', p.name)
    if m:
        map_base[m.group(2)] = p.name

non_root_files = []
for p in root.rglob('*'):
    if not p.is_file():
        continue
    if p.parent == root:
        continue
    if '.git' in p.parts:
        continue
    try:
        txt = p.read_text(encoding='utf-8')
    except Exception:
        continue
    refs = []
    for base, new in map_base.items():
        cnt = txt.count(base)
        if cnt:
            refs.append({'old': base, 'new': new, 'count': cnt})
    if refs:
        non_root_files.append({'file': str(p), 'refs': refs})

out = root / 'tmp' / 'nonroot_doc_ref_replace_candidates_20260318.json'
out.write_text(json.dumps(non_root_files, ensure_ascii=False, indent=2), encoding='utf-8')
print('files_with_candidates', len(non_root_files))
print('output', out)
