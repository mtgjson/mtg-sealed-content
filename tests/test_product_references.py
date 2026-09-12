import unittest
from scripts.reference_validator import reference_errors


class ProductReferenceTests(unittest.TestCase):
    def test_valid_cross_set_shared_and_placeholder_targets(self):
        a, b, c = ('a', 'Box'), ('b', 'Pack'), ('c', 'Box')
        products = {a, b, c}
        contents = {
            a: {'sealed': [{'set': 'B', 'name': 'Pack'}]},
            b: {},
            c: {'variable': [{'sealed': [{'set': 'b', 'name': 'Pack'}]}]},
        }
        self.assertEqual(reference_errors(products, contents), [])
        del contents[b]  # Known product with contents still awaiting research.
        self.assertEqual(reference_errors(products, contents), [])

    def test_missing_sealed_reference_inside_nested_variable(self):
        key = ('a', 'Box')
        errors = reference_errors({key}, {key: {'variable': [{'variable': [
            {'sealed': [{'set': 'b', 'name': 'Missing'}]}
        ]}]}})
        self.assertEqual(len(errors), 1)
        self.assertIn('missing sealed product', errors[0])
        self.assertIn('Missing', errors[0])

    def test_copy_target_must_have_contents(self):
        a, b = ('a', 'Copy'), ('a', 'Original')
        errors = reference_errors({a, b}, {a: {'copy': 'Original'}})
        self.assertEqual(len(errors), 1)
        self.assertIn('missing copy target', errors[0])
        self.assertEqual(reference_errors({a, b}, {a: {'copy': 'Original'}, b: {}}), [])

    def test_cross_set_cycle_through_variable_and_copy(self):
        a, b, c = ('a', 'Box'), ('b', 'Box'), ('b', 'Alias')
        errors = reference_errors({a, b, c}, {
            a: {'variable': [{'sealed': [{'set': 'b', 'name': 'Alias'}]}]},
            c: {'copy': 'Box'},
            b: {'sealed': [{'set': 'a', 'name': 'Box'}]},
        })
        self.assertEqual(len(errors), 1)
        self.assertIn('a/Box -> b/Alias -> b/Box -> a/Box', errors[0])

    def test_direct_self_reference(self):
        a = ('a', 'Box')
        errors = reference_errors({a}, {a: {'sealed': [{'set': 'a', 'name': 'Box'}]}})
        self.assertIn('a/Box -> a/Box', errors[0])
