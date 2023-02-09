#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import argparse

from typing import Optional
from detect_version import load_modules


def find_changes(name: str, attribute: Optional[str] = None) -> None:
    """ Find changes matching module name and optional attribute name.

        Args:
            name (str): the module name
            attribute (str): the optional attribute name
    """
    version_history = load_modules('modules.json')
    for module in version_history:
        if module.name != name:
            continue

        if attribute:
            for version, names in module.added.items():
                if attribute in names:
                    print(f'{module.name}.{attribute} requires {version}')
        else:
            if module.module_created:
                print(f'{module.name} module requires {module.module_created}')

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

    args = parser.parse_args()

    if len(args.name) > 2:
        parser.error('Invalid number of arguments (must be 1 or 2).')
    else:
        find_changes(*args.name)


if __name__ == '__main__':
    main()
