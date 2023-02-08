#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import argparse
from detect_version import load_changes
from typing import Optional


def find_changes(
        name: str,
        attribute: Optional[str] = None,
        list_all: Optional[bool] = False
        ) -> None:

    """ Find all module changes.

        Args:
            name (str): the module name
            attribute (str): an optional attribute name
            list_all (bool): list all module changes (only works with attribute=None)
    """
    version_history = load_changes('modules.json')
    for module in version_history:
        if module.name != name:
            continue

        if attribute:
            for version, names in module.added.items():
                if attribute in names:
                    print(f'{module.name}.{attribute} requires {version}')
        else:
            if module.created:
                version = module.created
                print(f'{module.name} module requires {version}')

            if list_all:
                for version, attributes in module.added.items():
                    for name in attributes:
                        print(f'{module.name}.{name} requires {version}')


def main():
    parser = argparse.ArgumentParser(
        description='Find specific module or attribute changes.',
        usage='%(prog)s [-h] [-a] module [attribute]')

    parser.add_argument(
        'name',
        metavar='module [attribute]',
        help='module with optional attribute name',
        nargs='+')

    parser.add_argument(
        '-a', '--all',
        help='show all module changes (only if no attribute is specified)',
        action='store_true')

    args = parser.parse_args()

    if len(args.name) > 2:
        parser.error('Invalid number of arguments (must be 1 or 2).')
    elif len(args.name) == 2 and args.all:
        parser.error('Cannot use --all with the attribute argument.')

    find_changes(*args.name, list_all=args.all)


if __name__ == '__main__':
    main()
