#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import argparse
import fnmatch
from src import Changelog, Requirement
from typing import Optional


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
        dict[str, dict]: dictionary of names and their requirements.
    """
    results = {}
    for name, changes in changelog.items():
        # Name filter
        if not fnmatch.fnmatch(name, pattern):
            continue

        # Action filter
        if action and action not in changes.keys():
            continue

        # Version filter
        if version and version not in changes.values():
            continue

        results[name] = changelog.get_requirement(name)

    return results


def main():
    desc = r"""Find specific version changes.

The name argument supports fnmatch-style pattern matching:

    * - matches everything
    ? - matches any single character
    [seq] - matches any character in seq
    [!seq] - matches any character not in seq
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=desc)

    parser.add_argument(
        'name',
        help='name or search pattern')

    parser.add_argument(
        '-v', '--version',
        help='limit results to a specific version')

    category_group = parser.add_mutually_exclusive_group()

    category_group.add_argument(
        '-m', '--modules',
        help='search modules (default)',
        action='store_true')

    category_group.add_argument(
        '-l', '--language',
        help='search language changes',
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

    parser.add_argument(
        '-s', '--sort-name',
        help='sort by name instead of version (default: False)',
        action='store_true')

    args = parser.parse_args()

    # Get changelog
    if args.exceptions:
        changelog = Changelog('data/exceptions.json')
    elif args.functions:
        changelog = Changelog('data/functions.json')
    elif args.language:
        changelog = Changelog('data/language.json')
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
    changes = find_changes(changelog, args.name, args.version, action)
    if changes:
        # Sort by name or by requirement first
        if args.sort_name:
            changes = sorted(changes.items())
        else:
            changes = sorted(changes.items(), key=lambda a: (a[1], a[0]))

        # Print header
        column = '{:<40} {:<12} {:<12} {:<12}'
        print(column.format('Name', 'Added', 'Deprecated', 'Removed'))

        # Print table
        blank_char = '-'
        for name, requirement in changes:
            print(column.format(name,
                                requirement.added or blank_char,
                                requirement.deprecated or blank_char,
                                requirement.removed or blank_char))

    matches = 'match.' if len(changes) == 1 else 'matches.'
    print('Found', len(changes), matches)


if __name__ == '__main__':
    main()
