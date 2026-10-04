import copy
import itertools
from pathlib import Path
import sys
import unittest

import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from product_classes import product


def outcomes(content):
    rows = [content.get('deck', [])]
    for group in content.get('variable', []):
        choices = [row for config in group['configs'] for row in outcomes(config)]
        rows = [a + b for a, b in itertools.product(rows, choices)]
    return rows


class NestedVariableTests(unittest.TestCase):
    def test_repeated_component_keeps_two_independent_choices(self):
        source = {'variable': [{'variable': [
            {'deck': [{'set': 'tst', 'name': 'A'}]},
            {'deck': [{'set': 'tst', 'name': 'B'}]},
        ]}], 'variable_mode': {'count': 2, 'replacement': True}}
        original = copy.deepcopy(source)
        p = product(source)
        self.assertEqual(source, original)
        self.assertEqual([[d['name'] for d in row] for row in outcomes(p.toJson())],
                         [['A', 'A'], ['A', 'B'], ['B', 'A'], ['B', 'B']])
        # Reference validation must traverse every independent group.
        p.get_uuids({'tst': {'decks': {'A': {}, 'B': {}}}})

    def test_battle_pack_color_constraints(self):
        root = Path(__file__).resolve().parents[1]
        for code, count in [('M12', 80), ('M13', 1600)]:
            data = yaml.safe_load((root / 'data/products' / (code + '.yaml')).read_text())
            contents = next(v['contents'] for k, v in data['products'].items()
                            if k.endswith('Booster Battle Pack'))
            rows = outcomes(product(contents).toJson())
            self.assertEqual(len(rows), count)
            self.assertEqual(contents['card_count'], 70)
            for row in rows:
                self.assertEqual(len(row), 4)
                colors = [d['name'].split(': ')[1].rsplit(' ', 1)[0] for d in row]
                if code == 'M12':
                    self.assertEqual(len(set(colors)), 4)
                else:
                    self.assertEqual(len(set(colors[:2])), 2)
                    self.assertEqual(len(set(colors[2:])), 2)
            if code == 'M13':
                self.assertTrue(any(row[:2] == row[2:] for row in rows))


if __name__ == '__main__':
    unittest.main()
