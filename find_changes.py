#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import argparse
import fnmatch

from detect_version import Changelog, Requirement, version_tuple
from typing import Optional

# Constants
VALID_ACTIONS = ('added', 'removed', 'deprecated')


def find_changes(changelog: Changelog,
                 pattern: str,
                 version: Optional[str] = None,
                 action: Optional[str] = None
                 ) -> dict[str, Requirement]:
    """ Find changes based on the search criteria.

    Args:
        changelog (dict): the changelog to search.
        pattern (str): the search pattern.
        version (str, optional): limit results to a specific version.
        action (str, optional): limit results to a specific action.

    Returns:
        dict[str, dict]: matching names and their requirements.
    """
    results = {}
    for name, changes in changelog.items():
        if fnmatch.fnmatch(name, pattern):
            if action and action not in changes.keys():
                continue

            if version and version not in changes.values():
                continue

            results[name] = changes
    return results


def main():
    desc = r"""Find specific version changes.

The name argument supports fnmatch-style pattern matching:

    * - matches everything
    ? - matches any single character
    [seq] - matches any character in seq
    [!seq] - matches any character not in seq

Wildcards * need to be escaped with quotes when used from a command line.

    For example "os.*"
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=desc)

    parser.add_argument(
        'name',
        help='name of the module, class, attribute, function, or exception')

    parser.add_argument(
        '-v', '--version',
        help='limit results to a specific version')

    category_group = parser.add_mutually_exclusive_group()

    category_group.add_argument(
        '-m', '--modules',
        help='search modules (default)',
        action='store_true')

    category_group.add_argument(
        '-e', '--exceptions',
        help='search exceptions',
        action='store_true')

    category_group.add_argument(
        '-f', '--functions',
        help='search functions',
        action='store_true')

    action_group = parser.add_mutually_exclusive_group()

    action_group.add_argument(
        '-a', '--added',
        help='include results that have added versions',
        action='store_true'
    )

    action_group.add_argument(
        '-d', '--deprecated',
        help='include results that have deprecated versions',
        action='store_true'
    )

    action_group.add_argument(
        '-r', '--removed',
        help='include results that have removed versions',
        action='store_true'
    )
    args = parser.parse_args()

    # Get changelog category
    if args.exceptions:
         changelog = Changelog('data/exceptions.json')
    elif args.functions:
        changelog = Changelog('data/functions.json')
    else:
        changelog = Changelog('data/modules.json')

    # Get action filter
    if args.added:
        action = 'added'
    elif args.deprecated:
        action = 'deprecated'
    elif args.removed:
        action = 'removed'
    else:
        action = None

    # Search for matches
    results = find_changes(changelog, args.name, args.version, action)
    if results:
        column = '{:<30} {}'
        for name, changes in results.items():
            print(column.format(name, changes))

    matches = 'match.' if len(results) == 1 else 'matches.'
    print('Found', len(results), matches)


if __name__ == '__main__':
    main()
