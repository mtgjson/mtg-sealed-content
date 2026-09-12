#!/usr/bin/env python3
"""Inventory an MTG release year; output candidates, never automatic fixes."""
import argparse
import json
from collections import Counter
from pathlib import Path
import yaml

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sealed', type=Path, required=True)
p.add_argument('--search', type=Path, required=True)
p.add_argument('--decks-json', type=Path, required=True)
p.add_argument('--year', type=int, required=True)
p.add_argument('--include-set', action='append', default=[])
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
sets = json.loads((a.search / 'index/sets.json').read_text())
decks = {(d['set_code'].lower(), d['name']): d for d in json.loads(a.decks_json.read_text())}
contents = {f.stem.lower(): (yaml.safe_load(f.read_text()) or {}).get('products', {})
            for f in (a.sealed / 'data/contents').glob('*.yaml')}
rows, issues, undated = [], [], []

def issue(product, kind, detail):
    issues.append({'product': product, 'kind': kind, 'detail': detail})

def scan(value, product, code, seen):
    if isinstance(value, list):
        for v in value:
            scan(v, product, code, seen)
    elif isinstance(value, dict):
        for key, values in value.items():
            if key == 'copy':
                target = (code, values)
                if target in seen:
                    issue(product, 'copy_cycle', values)
                elif values not in contents.get(code, {}):
                    issue(product, 'missing_copy', values)
                else:
                    scan(contents[code][values], product, code, seen | {target})
            elif key in ('deck', 'pack', 'sealed'):
                for r in values:
                    sc = r.get('set', code).lower()
                    if key == 'deck' and (sc, r['name']) not in decks:
                        issue(product, 'missing_deck', r)
                    elif key == 'sealed' and r['name'] not in contents.get(sc, {}):
                        issue(product, 'missing_sealed', r)
                    elif key == 'pack':
                        filename = sc + ('' if r['code'] == 'default' else '-' + r['code']) + '.yaml'
                        if not (a.search / 'data/boosters' / filename).exists():
                            issue(product, 'missing_pack', r)
            else:
                scan(values, product, code, seen)

for f in sorted((a.sealed / 'data/products').glob('*.yaml')):
    code = f.stem.lower()
    for name, info in (yaml.safe_load(f.read_text()) or {}).get('products', {}).items():
        if not isinstance(info, dict):
            continue
        explicit = info.get('release_date')
        date = str(explicit or sets.get(code, {}).get('release_date') or '')
        if not date:
            undated.append({'code': code, 'name': name})
        if not date.startswith(str(a.year)) and code not in a.include_set:
            continue
        product = code + '/' + name
        row = {'code': code, 'name': name, 'date': date,
               'date_source': 'product' if explicit else 'set' if date else 'manual',
               'category': info.get('category'), 'subtype': info.get('subtype')}
        rows.append(row)
        value = contents.get(code, {}).get(name)
        if not value:
            issue(product, 'empty_contents', {})
            continue
        scan(value, product, code, {(code, name)})
        if isinstance(value, dict) and value.get('deck'):
            refs = [(r.get('set', code).lower(), r['name']) for r in value['deck']]
            if all(r in decks for r in refs):
                count = sum(c['count'] for r in refs for section, cards in decks[r]['cards'].items()
                            if section != 'Display Commander' for c in cards if not c.get('token'))
                if count != value.get('card_count'):
                    issue(product, 'count_review', {'stored': value.get('card_count'),
                          'deck_gameplay_count': count, 'other_content_fields': sorted(set(value) - {'deck', 'card_count'})})
result = {'year': a.year, 'products': rows, 'issues': issues,
          'undated_products': undated,
          'limits': ['Date-selected catalog entries, not proof of complete SKU coverage.',
                     'Count differences require manual review of mixed products and gameplay tokens.',
                     'Pack existence checks do not compile queries or verify slot probabilities.']}
a.output.write_text(json.dumps(result, indent=2, default=str) + '\n')
print(json.dumps({'products': len(rows), 'sets': dict(Counter(r['code'] for r in rows)),
                  'issues': dict(Counter(i['kind'] for i in issues)), 'undated': len(undated)}, indent=2))
