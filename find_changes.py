#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import argparse
from detect_version import load_changes


def find_changes(module_name, attribute=None, list_all=False):
    """ Find and print module changes. """
    for (version, module, additions) in load_changes():
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
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'search',
        help='module or attribute to search for',
        nargs='+')

    parser.add_argument(
        '-a', '--all',
        help='show all module changes (only if no attributes are specified)',
        action='store_true')

    args = parser.parse_args()

    if len(args.search) == 1:
        find_changes(args.search[0], list_all=args.all)
    elif len(args.search) == 2:
        find_changes(args.search[0], args.search[1])
    else:
        parser.error('Invalid number of arguments')


if __name__ == '__main__':
    main()
