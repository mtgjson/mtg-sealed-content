"""Validate local sealed/copy references without requiring MTGJSON downloads."""
from pathlib import Path
import yaml


def reference_errors(product_names, contents):
    errors = []
    graph = {key: set() for key in contents}

    def visit_contents(source, value):
        if not isinstance(value, dict):
            return
        if set(value) == {'copy'}:
            target = (source[0], value['copy'])
            if target not in contents:
                errors.append(f'{source}: missing copy target {target}')
            else:
                graph[source].add(target)
            return
        for entry in value.get('sealed', []):
            target = (entry['set'].lower(), entry['name'])
            if target not in product_names:
                errors.append(f'{source}: missing sealed product {target}')
            if target in contents:
                graph[source].add(target)
        for choice in value.get('variable', []):
            visit_contents(source, choice)

    for source, value in contents.items():
        visit_contents(source, value)

    completed = set()
    active = set()
    trail = []

    def visit(node):
        if node in active:
            cycle = trail[trail.index(node):] + [node]
            errors.append('Product reference cycle: ' + ' -> '.join(f'{s}/{n}' for s, n in cycle))
            return
        if node in completed:
            return
        active.add(node)
        trail.append(node)
        for target in sorted(graph[node]):
            visit(target)
        trail.pop()
        active.remove(node)
        completed.add(node)

    for node in sorted(graph):
        visit(node)
    return errors


def validate_references():
    product_names = set()
    contents = {}
    for folder, target in (('products', product_names), ('contents', contents)):
        for path in sorted(Path('data', folder).glob('*.yaml')):
            with path.open() as stream:
                data = yaml.safe_load(stream)
            for name, value in data['products'].items():
                key = (data['code'].lower(), name)
                if folder == 'products':
                    target.add(key)
                else:
                    target[key] = value
    errors = reference_errors(product_names, contents)
    if errors:
        raise ValueError('\n'.join(errors))
