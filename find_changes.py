#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import argparse
from detect_version import load_changes

from typing import Optional


def find_changes(
        module_name: str,
        attribute: Optional[str] = None,
        list_all: Optional[bool] = False
        ) -> None:

    """ Find and print module changes. """
    version_history = load_changes()
    for version, changes in version_history.items():
        for module, additions in changes.items():
            if module_name == module:
                if not attribute:
                    if not additions:
                        print(f'Added {module} module in {version}')
                    elif additions and list_all:
                        for addition in additions:
                            print(f'Added {module}.{addition} in {version}')
                elif attribute and attribute in additions:
                    print(f'Added {module}.{attribute} in {version}')


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
