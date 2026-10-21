import copy
import unittest

from mtg_sealed_choices import ChoiceGroups


class Component:
    def __init__(self, source):
        self.labels = source.get("labels", [])[:]
        self.chance = source.get("chance", 1)
        self.weight = source.get("weight", 0)
        self.choices = ChoiceGroups(source, Component)

    def merge(self, other):
        self.labels += other.labels
        self.chance *= other.chance
        self.choices.merge(other.choices)

    def serialize(self):
        return {"labels": self.labels, "chance": self.chance, "weight": self.weight,
                "variable": self.choices.serialize(Component.serialize)}


class ChoiceTests(unittest.TestCase):
    def test_weighted_combinations(self):
        for replacement, expected in [(False, [(6, 6)]), (True, [(4, 19), (6, 19), (9, 19)])]:
            source = {"variable": [{"chance": 2}, {"chance": 3}],
                      "variable_mode": {"count": 2, "replacement": replacement}}
            before = copy.deepcopy(source)
            result = Component(source)
            self.assertEqual([(c.chance, c.weight) for c in result.choices.groups[0]], expected)
            self.assertEqual(source, before)

    def test_nested_groups_stay_independent(self):
        source = {"variable": [{"variable": [{"labels": ["A"]}, {"labels": ["B"]}]}],
                  "variable_mode": {"count": 2, "replacement": True}}
        child = Component(source).choices.groups[0][0]
        self.assertEqual(len(child.choices.groups), 2)
        self.assertEqual([[c.labels for c in g] for g in child.choices.groups],
                         [[["A"], ["B"]], [["A"], ["B"]]])
        self.assertEqual(len(child.serialize()["variable"]), 2)

    def test_explicit_weights_and_invalid_total(self):
        source = {"variable": [{"chance": 2}, {"chance": 3}], "variable_mode": {"weight": 5}}
        self.assertEqual([c.weight for c in Component(source).choices.groups[0]], [5, 5])
        source["variable_mode"]["weight"] = 6
        with self.assertRaisesRegex(ValueError, "Weight incorrectly assigned"):
            Component(source)

    def test_plain_alternatives_preserve_weights(self):
        result = Component({"variable": [{"chance": 2, "weight": 3}, {"chance": 1, "weight": 3}]})
        self.assertEqual([(c.chance, c.weight) for c in result.choices.groups[0]], [(2, 3), (1, 3)])

    def test_empty_and_zero_selection(self):
        self.assertEqual(Component({}).choices.serialize(Component.serialize), [])
        result = Component({"variable": [{"labels": ["A"]}], "variable_mode": {"count": 0}})
        self.assertEqual(len(result.choices.groups[0]), 1)
        self.assertEqual(result.choices.groups[0][0].labels, [])


if __name__ == "__main__":
    unittest.main()
