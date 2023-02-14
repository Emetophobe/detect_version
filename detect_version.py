#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import ast
import csv
import sys
import sqlite3
import argparse

from typing import Optional
from os import PathLike


# ACTION constants
ACTION_ADDED = 'added'
ACTION_DEPRECATED = 'deprecated'
ACTION_REMOVED = 'removed'
ALL_ACTIONS = (ACTION_ADDED, ACTION_DEPRECATED, ACTION_REMOVED)


class Changelog:
    """ A simple changelog database backed by csv files.

        Changelogs are stored as csv files (plain text) instead of
        sqlite (binary) for easier git diffs and tracking changes.

        This class simply creates an in-memory sqlite3 database
        with rows loaded from csv files.
    """

    def __init__(self) -> None:
        """ Initialize the database connection. """
        self.conn = sqlite3.connect(':memory:')
        self.conn.create_collation('collate_version', compare_version)
        self._create_tables()

    def get_module(self, module: str) -> list[tuple]:
        """ Get module changes matching the specified module name. """
        sql = 'SELECT * FROM modules WHERE name = ?'
        return self.query(sql, (module,))

    def get_function(self, function: str) -> list[tuple]:
        """ Get function changes matching the specified function name. """
        sql = 'SELECT * FROM functions WHERE name = ?;'
        return self.query(sql, (function,))

    def get_exception(self, exception: str) -> list[tuple]:
        """ Get exception changes matching the specified exception name. """
        sql = 'SELECT * FROM exceptions WHERE name = ?;'
        return self.query(sql, (exception,))

    def query(self, sql: str, args: tuple | list) -> list[tuple]:
        """ Convenience method to query the database. """
        cursor = self.conn.cursor()
        cursor.execute(sql, args)
        return cursor.fetchall()

    def close(self):
        """ Close the database connection. """
        if self.conn:
            self.conn.close()

    def _create_tables(self):
        """ Initialize the database tables. """
        # Dictionary of table names and their associated csv files
        # Plain-text csv files are easier to track in a git repository
        # than a binary sqlite file.
        tables = {
            'modules': 'changelogs/modules.csv',
            'exceptions': 'changelogs/exceptions.csv',
            'functions': 'changelogs/functions.csv'
        }

        # Create individual database tables and insert csv rows
        for table, filename in tables.items():
            cur = self.conn.cursor()
            cur.execute(f'CREATE TABLE {table} (version TEXT NOT NULL, action TEXT NOT NULL, '
                        'name TEXT NOT NULL);')
            cur.executemany(f'INSERT INTO {table} (version, action, name) VALUES '
                            '(?, ?, ?);', load_changes(filename))
            self.conn.commit()


class Analyzer(ast.NodeVisitor):
    """ Parse abstract syntax tree and determine a minimum required script version. """

    def __init__(self, script: PathLike) -> None:
        """ Initialize node analyzer.

        Args:
            script (PathLike): script filename.
        """
        self.changelog = Changelog()
        self.requirements = {}
        self.script = script

        # Versions are internally stored as strings instead of floats to
        # prevent Python versions like 3.10 being simplified down to 3.1
        self.min_version = '3.0'

    def report(self) -> None:
        """ Report script requirements. """
        warnings = {}

        # Sort requirements by version (compare strings by converting to a tuple first)
        requirements = sorted(self.requirements.items(),
                              key=lambda a: (version_tuple(a[1][0]), a[0]))

        # Print minimum detected script version and detailed requirements
        print(f'{self.script}: requires {self.min_version}')
        for feature, changes in requirements:
            added, removed, deprecated = changes
            # Print requirements
            if added:
                print(f'  {feature} requires {added}')

            # Build dictionary of deprecations and removals
            elif deprecated or removed:
                warnings[feature] = (deprecated, removed)

        # Print warning about deprecations and removals
        if warnings:
            print()
            print('Warning: Found deprecated or removed features:')
            for feature, changes in warnings.items():
                deprecated, removed = changes
                if deprecated:
                    print(f'  {feature} deprecated in version {deprecated}')
                if removed:
                    print(f'  {feature} removed in version {removed}')

        # Close database
        self.changelog.close()

    def update_requirements(self, feature: str, changes: tuple | list[tuple]) -> None:
        """ Update script requirements.

        Args:
            feature (str): Name of the feature.
            changes (tuple | list[tuple]): Single change or a list of changes.

        Raises:
            TypeError: If the changes are an invalid type.
        """
        # Convert tuple to a list of tuples
        if isinstance(changes, tuple):
            changes = [changes]
        if not isinstance(changes, list):
            raise TypeError(f'Unsupported type. Expected a tuple or list,'
                            f' received a {type(changes)}')

        # Convert changes to a 3-tuple of version strings (added, deprecated, removed)
        # TODO: find a much nicer way to implement this
        versions = {}
        for row in changes:
            versions[row[1]] = row[0]
        requirements = tuple(versions.get(version, None) for version in ALL_ACTIONS)

        # Check if the feature is already added
        if feature in self.requirements.keys() and self.requirements[feature] == requirements:
            return

        # Update requirements
        self.update_version(requirements[0])
        self.requirements[feature] = requirements

    def update_version(self, version: str) -> None:
        """ Update minimum script version.

        Args:
            version (str): The version string.
        """
        if not version:
            return

        # Convert version strings to tuples temporarily for comparison
        if version_tuple(version) > version_tuple(self.min_version):
            self.min_version = version

    def visit_Import(self, node: ast.Import) -> None:
        """ Scan import statements for module changes.

            node.names is the list of imports (i.e "import a, b, c")
        """
        for alias in node.names:
            self._check_module(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """ Scan "from x import a, b, c" import statements for module changes.

            node.module is the module name (i.e "from x")
            node.names is the list of imports (i.e "import a, b, c")
        """
        for alias in node.names:
            # Handle wildcard "from module import *"
            if alias.name == '*':
                self._check_module(node.module)
            else:
                self._check_module(node.module + '.' + alias.name)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """ Check for module attribute changes.

            node.value is a node that can be a Name or an Attribute.
            node.attr is a string of the attribute name.
            node.ctx is the context of the attribute access (Load, Store or Del).
        """
        self._check_attribute(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """ Check for function changes.

            node.func is the function (which can be a Name or Attribute node).
        """
        if isinstance(node.func, ast.Name):
            self._check_function(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self._check_attribute(node.func)
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        """ Check raised exceptions for new exceptions types.

            node: A raise statement (represented as a Raise node).

            node.exc: The exception being raised, normally a Call or Name node,
                      or None for a standalone raise.

            node.cause (optional): the optional from clause (i.e raise x from y).

        """
        if isinstance(node.exc, ast.Call):
            self._check_exception(node.exc.func.id)
        elif isinstance(node.exc, ast.Name):
            self._check_exception(node.exc.id)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """ Check caught exceptions for new exceptions types.

            node: a single except clause.

            node.type: name of the exception, typically a Name node (or None
                       for a catch-all except: clause)

            node.name (optional): name of stored exception or None if none was
                       given. It's the "as x" in "except TypeError as x")
        """
        self._check_exception(node.type.id)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        """ Check for unicode literals which were added in Python 3.3.

            node: Represents a constant value or literal.
            node.value: The string value.
            node.kind: "u" for unicode string, None otherwise.
        """
        if node.kind == 'u':
            self.update_requirements('unicode literal', self._create_requirement('3.3'))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AST):
        """ Check for async/await reserved keywords which were added in Python 3.7

            Python 3.5 introduced async/await but they were only treated as keywords
            inside the body of a coroutine function.

            Python 3.7 changed async/await to reserved keywords (like 'if' and 'else')

            This introduced some backwards incompatible syntax changes between the 3.5
            and 3.7 versions of async/await. I will only be testing against Python 3.7
            where they became full reserved keywords.
        """
        self.update_requirements('async and await', self._create_requirement('3.7'))
        self.generic_visit(node)

    # Use same method for all async/await visitors
    visit_AsyncFor = visit_AsyncWith = visit_Await = visit_AsyncFunctionDef

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """ Check for fstring literals which were added in Python 3.6 """
        self.update_requirements('fstring literal', self._create_requirement('3.6'))
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        """ Check for walrus operators which were added in Python 3.8 """
        self.update_requirements('walrus operator', self._create_requirement('3.8'))
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """ Check for match/case statements which were added in Python 3.10 """
        self.update_requirements('match statement', self._create_requirement('3.10'))
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """ Check for multiple context managers which were added in Python 3.1 """
        if len(node.items) > 1:
            self.update_requirements('multiple with clauses', self._create_requirement('3.1'))
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        """ Check for "yield from" expressions which were added in Python 3.3 """
        self.update_requirements('yield from expression', self._create_requirement('3.3'))
        self.generic_visit(node)

    def _check_exception(self, exception: str) -> None:
        """ Check for new exception types. """
        changes = self.changelog.get_exception(exception)
        if changes:
            self.update_requirements(exception, changes)

    def _check_function(self, function: str) -> None:
        """ Check for new function names. """
        changes = self.changelog.get_function(function)
        if changes:
            self.update_requirements(f'{function} function', changes)

    def _check_module(self, module: str) -> None:
        """ Check for module changes. """
        changes = self.changelog.get_module(module)
        if changes:
            self.update_requirements(module, changes)

    def _check_attribute(self, node: ast.Attribute) -> None:
        """ Check for module attribute changes. """
        # Get full module+attribute name from a potentially nested Attribute
        self._check_module(self._get_attribute(node))

    def _get_attribute(self, node: ast.Name | ast.Attribute) -> str:
        """ Combine nested attributes into a single string. """
        if isinstance(node, ast.Name):
            return str(node.id)
        elif isinstance(node, ast.Attribute):
            return str(self._get_attribute(node.value) + '.' + node.attr)
        else:
            return str()

    def _create_requirement(self, version: str, action: Optional[str] = ACTION_ADDED,
                            name: Optional[str] = None) -> tuple:
        """ Convenience method to create a single requirement tuple. """
        return (version, action, name)


def detect_version(filename: str | bytes) -> None:
    """ Analyze Python script and print requirements. """
    with open(filename, 'r') as source:
        tree = ast.parse(source.read())

    analyzer = Analyzer(filename)
    analyzer.visit(tree)
    analyzer.report()


def version_tuple(version: str) -> tuple[int, int, int]:
    """ Split a version string into a tuple. Example: "3.11.1" returns (3, 11, 1) """
    if not version:
        return tuple()
    return tuple(map(int, (version.split('.'))))


def compare_version(version1: str, version2: str) -> bool:
    """ Compare two version strings by temporarily converting them to tuples. """
    if version_tuple(version1) > version_tuple(version2):
        return 1
    elif version_tuple(version1) == version_tuple(version2):
        return 0
    else:
        return -1


def load_changes(filename: str | PathLike) -> None:
    """ Load changelog from csv file. """
    csv.register_dialect('custom_csv', 'unix', skipinitialspace=True)
    with open(filename, 'r', newline='') as infile:
        return list(csv.reader(infile, dialect='custom_csv'))


def dump_file(path: str | PathLike) -> None:
    """ Parse script and dump tree to stdout. """
    with open(path, 'r') as source:
        dump_node(ast.parse(source.read()))


def dump_node(node: ast.AST) -> None:
    """ Convenience function to print contents of a node. """
    print(ast.dump(node, indent=4))


def main():
    desc = 'Detect the minimum required version of a Python script.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('path', help='python script to scan')
    parser.add_argument('-d', '--dump', help='dump ast to stdout', action='store_true')
    args = parser.parse_args()

    try:
        if args.dump:
            dump_file(args.path)
        else:
            detect_version(args.path)
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)


if __name__ == '__main__':
    main()
