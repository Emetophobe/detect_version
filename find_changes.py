#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import argparse

from detect_version import Changelog
from typing import Optional
from os import PathLike


def find_changes(name: str | PathLike,
                 version: Optional[str] = None,
                 action: Optional[str] = None
                 ) -> list[tuple]:
    """ Search the module changelog for specific version changes.

    Args:
        name (str or PathLike): Module or attribute name. SQL-like % patterns are allowed.
        version (str, optional): Select a specific version Defaults to None.
        action (str, optional): Select a specific action ("added", "deprecated", or "removed")

    Returns:
        list[tuple]: The matching database rows, if any.
    """

    # Load sqlite database
    changelog = Changelog()

    # Build sql statement and argument list
    sqlbuilder = ['SELECT * FROM modules']
    where = []
    args = []

    # Match exact name or like name using '%'.
    if name.startswith('%') or name.endswith('%'):
        where.append('NAME LIKE ?')
    else:
        where.append('NAME = ?')
    args.append(name)

    # WHERE version = ? clause
    if version:
        where.append('VERSION = ?')
        args.append(version)

    # WHERE action = ? clause
    if action:
        where.append('ACTION = ?')
        args.append(action)

    # Add WHERE clauses
    if where:
        sqlbuilder.append('WHERE')
        for index, clause in enumerate(where):
            if index != 0:
                sqlbuilder.append('AND')
            sqlbuilder.append(clause)

    # Sort by version string using custom collate function
    sqlbuilder.append('ORDER BY version COLLATE collate_version')

    # Create sql statement and perform the query
    sql = ' '.join(sqlbuilder)
    cursor = changelog.conn.cursor()
    cursor.execute(sql, args)
    return cursor.fetchall()


def main():
    desc = """Utility script to find specific changes in the changelog.

The name argument can use SQL LIKE patterns with the percent %% symbol.

For example:

    % matches all names
    example% matches names that start with "example"
    %%example% matches names that have "example" in the middle
    %%example matches names that end with "example"
    """
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        'name',
        help='module or attribute name (Use "*" to match all names, "%%" to match similar names)')

    parser.add_argument(
        '-l', '--like',
        help='find similar names instead of an exact match',
        action='store_true')

    parser.add_argument(
        '-v', '--version',
        help='optional version number')

    parser.add_argument(
        '-a', '--action',
        help='optional action (added, deprecated, or removed)')

    args = parser.parse_args()

    results = find_changes(args.name, args.version, args.action)

    if results:
        columns = '{:<8} {:<15} {}'
        print(columns.format('Version', 'Action', 'Name'))
        for row in results:
            print(columns.format(*row))

    print('Found', len(results), 'row.' if len(results) == 1 else 'rows.')


if __name__ == '__main__':
    main()
