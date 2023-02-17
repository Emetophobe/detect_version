#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import ast
import csv
import sys
import argparse
import sqlite3
import functools

from typing import Optional
from os import PathLike


class Requirement:
    """ The requirement class is used to store a feature's version history.

    Attributes:

        added: Version when feature was introduced.
        deprecated: Version when feature was deprecated.
        removed: Version when feature was removed.

    A requirement can have any of the versions or None of them (no requirement).

    Versions are stored as strings because there is no way to represent versions
    like "3.11.1" as a float. The downside to strings is that the versions need
    to be converted to tuples temporarily when sorting.

    Examples:

        Requirement(None, None, None)       # no requirements
        Requirement("3.11.1", None, None)   # added in 3.11.1
        Requirement(None, "3.9", "3.12")    # deprecated in 3.9, removed in 3.12

    """
    def __init__(self, added: Optional[str] = None, deprecated: Optional[str] = None,
                 removed: Optional[str] = None) -> None:
        """ Initialize feature requirement.

        Args:
            added (str, optional):
                Version when feature was introduced. Defaults to None.

            deprecated (str, optional):
                Version when feature was deprecated. Defaults to None.

            removed (str, optional):
                Version when feature was removed. Defaults to None.
        """
        self.added = added
        self.deprecated = deprecated
        self.removed = removed

    def __lt__(self, other: object) -> bool:
        """ Less than "<" operator. Used for sorting requirements. """
        if not isinstance(other, Requirement):
            raise TypeError(f'Expected a Requirement, received a {type(other).__name__}')

        # zip both instances and compare added, deprecated, and removed one at a time
        for version, other_ver in zip(self, other):
            if compare_version(version, other_ver) < 0:
                return True
            elif compare_version(version, other_ver) == 0:
                continue
            else:
                return False
        return False

    def __eq__(self, other: object) -> bool:
        """ Equal "==" operator. Compare two requirements. """
        if not isinstance(other, Requirement):
            return False

        return (self.added == other.added and
                self.deprecated == other.deprecated and
                self.removed == other.removed)

    def __iter__(self):
        yield self.added
        yield self.deprecated
        yield self.removed

    def __str__(self) -> str:
        return f'{self.added}, {self.deprecated}, {self.removed}'


class Changelog:
    """ A simple sqlite3 database for searching csv files.

        Changelogs are stored as csv files (plain text) instead of
        sqlite files (binary) for easier git diffs and updates.

        This class simply creates an in-memory sqlite3 database
        with rows loaded from csv files.
    """

    def __init__(self) -> None:
        """ Initialize the database. """
        self.conn = sqlite3.connect(':memory:')
        self.conn.create_collation('collate_version', compare_version)
        self._create_table('modules', 'data/modules.csv')
        self._create_table('exceptions', 'data/exceptions.csv')
        self._create_table('functions', 'data/functions.csv')

    def query(self, sql: str, args: list | tuple, sort: bool = True) -> list[tuple]:
        """ Query the database for changes.

        Args:
            sql (str):
                The sql statement to execute.

            args (list | tuple):
                Sequence of parameterized arguments.

            sort (bool, optional):
                Sort rows by version. Defaults to True.

        Returns:
            list[tuple]:
                A list of rows or an empty list if no rows are found.
        """

        if sort:
            sql += ' ORDER BY version COLLATE collate_version'

        cursor = self.cursor()
        cursor.execute(sql, args)
        return cursor.fetchall()

    def get_requirement(self, sql: str, args: list | tuple) -> Requirement:
        """ Get a Requirement from the database.

        Args:
            sql (str): The sql statement to execute.
            args (list | tuple): Sequence of parameterized arguments.

        Returns:
            Requirement: The version requirements.
        """
        # Build requirements from query rows (key=action, value=version)
        requirements = {row[1]: row[0] for row in self.query(sql, args)}
        return Requirement(**requirements)

    @functools.lru_cache()
    def get_module(self, name: str) -> Requirement:
        """ Find module and attribute changes.

        Args:
            name (str): Name of the module or attribute.

        Returns:
            Requirement: The module requirements.
        """
        sql = 'SELECT * FROM modules WHERE name = ?'
        return self.get_requirement(sql, (name,))

    @functools.lru_cache()
    def get_function(self, function: str) -> Requirement:
        """ Find function changes.

        Args:
            function (str): Name of the function.

        Returns:
            Requirement: The function requirements.
        """
        sql = 'SELECT * FROM functions WHERE name = ?'
        return self.get_requirement(sql, (function,))

    def get_exception(self, exception: str) -> Requirement:
        """ Find exception changes.

        Args:
            exception (str): Name of the exception.

        Returns:
            Requirement: The exception requirements.
        """
        sql = 'SELECT * FROM exceptions WHERE name = ?'
        return self.get_requirement(sql, (exception,))

    def close(self) -> None:
        """ Close the database connection. """
        if self.conn:
            self.conn.close()

    def cursor(self) -> sqlite3.Cursor:
        """ Convenience method to retrieve a database cursor. """
        return self.conn.cursor()

    def _create_table(self, tablename: str, filename: str) -> None:
        """ Create a database table and insert rows from file. """
        rows = load_changes(filename)
        cur = self.conn.cursor()
        cur.execute(f'CREATE TABLE {tablename} (version TEXT NOT NULL,'
                     'action TEXT NOT NULL, name TEXT NOT NULL);')
        cur.executemany(f'INSERT INTO {tablename} (version, action, name) '
                         'VALUES (?, ?, ?);', rows)
        self.conn.commit()


class Analyzer(ast.NodeVisitor):
    """ Parse abstract syntax tree and find script requirements. """

    def __init__(self, filename: str | PathLike) -> None:
        """ Initialize node analyzer.

        Args:
            filename (PathLike): Filename of the script.
        """
        self.filename = filename
        self.changelog = Changelog()
        self.requirements = {}

        # Set minimum version to Python 3.0 (this has not be tested with 2.x)
        self.min_version = '3.0'
        # Note: Python versions are always stored as strings. There is no way
        # represent versions like "3.11.1" with a float. Floats also remove
        # trailing 0s and turn versions like 3.10 into 3.1


    def report(self) -> None:
        """ Print script requirements. """

        # Sort requirements by version then feature
        requirements = sorted(self.requirements.items(), key=lambda a: (a[1], a[0]))

        # Print minimum version
        print(f'{self.filename}: requires {self.min_version}')

        # Print requirements
        warnings = {}
        for feature, requirement in requirements:
            # Print added features
            if requirement.added:
                print(f'  {feature} requires {requirement.added}')

            # Build dictionary of deprecations and removals
            elif requirement.deprecated or requirement.removed:
                warnings[feature] = requirement

        # Print warning about deprecated and removed features
        if warnings:
            print()
            print('Warning: Found deprecated or removed features:')
            for feature, changes in warnings.items():
                if changes.deprecated:
                    print(f'  {feature} deprecated in version {changes.deprecated}')
                if changes.removed:
                    print(f'  {feature} removed in version {changes.removed}')

        # Close database
        self.changelog.close()

    def update_requirements(self, feature: str, requirement: Requirement) -> None:
        """ Update script requirements.

        Args:
            feature (str): Name of the feature.
            requirement (Requirement): The feature requirements.

        Raises:
            TypeError: If the requirement is an invalid type.
        """
        if not isinstance(requirement, Requirement):
            raise TypeError(f'Unsupported type. Expected a Requirement,'
                            f' received a {type(requirement)}')

        # Check if the feature is already added
        if feature in self.requirements.keys() and self.requirements[feature] == requirement:
            return

        # Update requirements
        self.update_version(requirement.added)
        self.requirements[feature] = requirement


    def update_version(self, version: str) -> None:
        """ Update minimum script version.

        Args:
            version (str): The version string.
        """
        if not version:
            return

        # Update version if newer
        if compare_version(version, self.min_version) > 0:
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
            self.update_requirements('unicode literal', Requirement('3.3'))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AST):
        """ Check for async/await reserved keywords which were added in Python 3.7

            Python 3.5 introduced async and await but they were only treated as
            keywords inside the body of a coroutine function.

            Python 3.7 changed async/await to reserved keywords. This introduced
            some backwards incompatible syntax changes between the 3.5 and 3.7
            versions of async/await.
        """
        self.update_requirements('async and await', Requirement('3.7'))
        self.generic_visit(node)

    # Use same method for all async/await visitors
    visit_AsyncFor = visit_AsyncWith = visit_Await = visit_AsyncFunctionDef

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """ Check for fstring literals which were added in Python 3.6 """
        self.update_requirements('fstring literal', Requirement('3.6'))
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        """ Check for walrus operators which were added in Python 3.8 """
        self.update_requirements('walrus operator', Requirement('3.8'))
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """ Check for match/case statements which were added in Python 3.10 """
        self.update_requirements('match statement', Requirement('3.10'))
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """ Check for multiple context managers which were added in Python 3.1 """
        if len(node.items) > 1:
            self.update_requirements('multiple with clauses', Requirement('3.1'))
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        """ Check for "yield from" expressions which were added in Python 3.3 """
        self.update_requirements('yield from expression', Requirement('3.3'))
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
            self.update_requirements(function + ' function', changes)

    def _check_module(self, module: str) -> None:
        """ Check for module changes. """
        changes = self.changelog.get_module(module)
        if changes:
            self.update_requirements(module, changes)

    def _check_attribute(self, node: ast.Attribute) -> None:
        """ Check for module attribute changes. """
        # Get the full module.attribute name from a potentially nested Attribute
        self._check_module(self._get_attribute_name(node))

    def _get_attribute_name(self, node: ast.Name | ast.Attribute) -> str:
        """ Combine nested attribute name into a single string. """
        if isinstance(node, ast.Name):
            return str(node.id)
        elif isinstance(node, ast.Attribute):
            return str(self._get_attribute_name(node.value) + '.' + node.attr)
        else:
            return str()


def version_tuple(version: str) -> tuple[int, int, int]:
    """ Split a version string into a tuple. For example "3.11.1" returns (3, 11, 1)

    Args:
        version (str):
            The version number.

    Returns:
        tuple[int, int, int]:
            Tuple of major, minor, micro versions.
    """
    if not version:
        return tuple()
    return tuple(map(int, (version.split('.'))))


def compare_version(version1: str, version2: str) -> int:
    """ Compare two version strings.

    Args:
        version1 (str):
            First version.

        version2 (str):
            Second version.

    Returns:
        int:
            A number based on the result of the comparison.
            1 for greater than, 0 for equal, -1 for less than.
    """
    if version_tuple(version1) > version_tuple(version2):
        return 1
    elif version_tuple(version1) == version_tuple(version2):
        return 0
    else:
        return -1


def load_changes(filename: str | PathLike) -> list[list]:
    """ Load changelog from a csv file.

    Args:
        filename (str | PathLike):
            Name of the csv file.

    Returns:
        list[list]:
            The list of csv rows.
    """
    csv.register_dialect('changelog', 'unix', skipinitialspace=True)
    with open(filename, 'r', newline='') as infile:
        return list(csv.reader(infile, dialect='changelog'))


def dump_file(filename: str | PathLike) -> None:
    """ Parse script and dump ast to stdout.

    Args:
        filename (str | PathLike):
            Filename of the script.
    """
    with open(filename, 'r') as source:
        dump_node(ast.parse(source.read()))


def dump_node(node: ast.AST) -> None:
    """ Print an ast node to stdout.

    Args:
        node (ast.AST):
            The ast node. Can also be any of the ast.AST node subclasses.

    """
    print(ast.dump(node, indent=4))


def detect_version(filename: str | PathLike) -> None:
    """Analyze a Python script and print the requirements.

    Args:
        filename (str | PathLike):
            Filename of the script.
    """
    with open(filename, 'r') as source:
        tree = ast.parse(source.read())

    analyzer = Analyzer(filename)
    analyzer.visit(tree)
    analyzer.report()


def main():
    desc = 'Detect Python script requirements using abstract syntax trees.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('path', help='python script (.py file)')
    parser.add_argument('-d', '--dump', help='dump script ast', action='store_true')
    parser.add_argument('--debug', help=argparse.SUPPRESS, action='store_true')
    args = parser.parse_args()

    try:
        if args.dump:
            dump_file(args.path)
        else:
            detect_version(args.path)
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)

    # For debugging only, print cache info
    if args.debug:
        print('get_module()', Changelog.get_module.cache_info())
        print('get_function()', Changelog.get_function.cache_info())


if __name__ == '__main__':
    main()
