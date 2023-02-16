#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import argparse

from detect_version import Changelog
from typing import Optional


def find_changes(name: str,
                 version: Optional[str] = None,
                 action: Optional[str] = None
                 ) -> list[tuple]:
    """ Search the module database for specific changes.

    Args:
        name (str): Module or attribute name.
        version (str, optional): Filter rows by version.
        action (str, optional): Filter rows by action.

    Returns:
        list[tuple]: List of matching rows, or an empty list if no rows were found.
    """
    # Open database
    changelog = Changelog()

    # Match exact name or like names.
    if name.startswith('%') or name.endswith('%'):
        sqlbuilder = ['SELECT * FROM modules WHERE name LIKE ?']
    else:
        sqlbuilder = ['SELECT * FROM modules WHERE name = ?']
    args = [name]

    # Version filter
    if version:
        sqlbuilder.append('AND VERSION = ?')
        args.append(version)

    # Action filter
    if action:
        sqlbuilder.append('AND ACTION = ?')
        args.append(action)

    # Create sql statement and perform the query
    sql = ' '.join(sqlbuilder)
    return changelog.query(sql, args, sort=True)


def main():
    desc = r"""Utility script to find specific module changes.

The name argument supports SQL-LIKE patterns using the percent % symbol:

    %       matches all names
    start%  matches names that begin with "start"
    %text%  matches names that have "text" in the middle
    %stop   matches names that end with "stop"
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=desc)
    parser.add_argument('name', help='module or attribute name')
    parser.add_argument('-v', '--version', help='Filter rows by version')
    parser.add_argument('-a', '--action', help='Filter rows by action')
    args = parser.parse_args()

    if args.action and args.action not in ('added', 'deprecated', 'removed'):
        parser.exit(f'Error: Invalid action: {args.action!r} (valid actions: '
                     'added, removed, deprecated)')

    results = find_changes(args.name, args.version, args.action)

    if results:
        columns = '{:<8} {:<13} {}'
        print(columns.format('Version', 'Action', 'Name'))
        for row in results:
            print(columns.format(*row))

    print('Found', len(results), 'row.' if len(results) == 1 else 'rows.')


if __name__ == '__main__':
    main()
