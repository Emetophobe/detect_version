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
    """ Search the module database for specific changes.

    Args:
        name (str or PathLike): Module or attribute name.
        version (str, optional): Optional version string.
        action (str, optional): Optioanl action name.

    Returns:
        list[tuple]: The database rows, if any.
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

    # Create sql statement and perform the query
    sql = ' '.join(sqlbuilder)
    return changelog.query(sql, args)


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
    parser.add_argument('-v', '--version', help='optional version number')
    parser.add_argument('-a', '--action', help='optional action name')
    args = parser.parse_args()

    results = find_changes(args.name, args.version, args.action)

    if results:
        columns = '{:<8} {:<13} {}'
        print(columns.format('Version', 'Action', 'Name'))
        for row in results:
            print(columns.format(*row))

    print('Found', len(results), 'row.' if len(results) == 1 else 'rows.')


if __name__ == '__main__':
    main()
