#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import argparse
from detect_version import load_modules
from typing import Optional


def find_changes(name: str, attribute: Optional[str] = None) -> None:
    """ Find changes matching a specific module or attribute.

        Args:
            name (str): The module name.
            attribute (str, optional): Optional attribute name. Defaults to None.
    """
    modules = load_modules('modules.json')

    # Find module
    try:
        module = modules[name]
    except KeyError:
        print('No module info.')
        return

    if attribute:
        # Find attribute
        if attribute in module.attributes.keys():
            print_requirement(f'{name}.{attribute}', module.attributes[attribute])
    else:
        # Print all module info
        if module.module_info:
            print_requirement(f'{name} module', module.module_info)

        # Print all module attribute info
        for attribute, changes in module.attributes.items():
            print_requirement(f'{name}.{attribute}', changes)


def print_requirement(feature, changes: dict):
    print(feature, requirement_string(changes))


def requirement_string(changes: dict) -> str:
    """ Create string from a dictionary. """
    builder = list()

    added = changes.get('added', None)
    deprecated = changes.get('deprecated', None)
    removed = changes.get('removed', None)

    if added:
        builder.append(f'requires {added}')

    if deprecated:
        prefix = '(' if added else 'was '
        builder.append(f'{prefix}deprecated in {deprecated}')

    if removed:
        if added and deprecated:
            prefix = ', '
        elif added:
            prefix = '('
        elif deprecated:
            prefix = 'and '
        else:
            prefix = ''
        builder.append(f'{prefix}removed in {removed}')

    end_curly = ')' if added and (deprecated or removed) else ''
    return f'{" ".join(builder)}{end_curly}'


def main():
    parser = argparse.ArgumentParser(
        description='Find specific module or attribute changes.',
        usage='%(prog)s [-h] [-a] module [attribute]')

    parser.add_argument(
        'name',
        metavar='module [attribute]',
        help='module with optional attribute name',
        nargs='+')

    args = parser.parse_args()

    if len(args.name) > 2:
        parser.error('Invalid number of arguments (must be 1 or 2).')
    else:
        find_changes(*args.name)


if __name__ == '__main__':
    main()
