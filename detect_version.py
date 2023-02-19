#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import ast
import json
import argparse

from pathlib import Path
from typing import Optional


class Requirement:
    """ A requirement holds a feature's version requirements.

    Attributes:

        added: Version when feature was introduced.
        deprecated: Version when feature was deprecated.
        removed: Version when feature was removed.

    A requirement can have one or more versions or None of them (no requirement).

    Versions are stored as strings because there is no way to represent versions
    like "3.11.1" as a float. The downside to strings is that the versions need
    to be converted to tuples temporarily when sorting (see version_tuple).

    Examples:

        Requirement(None, None, None)       # no requirements
        Requirement("3.5", None, None)      # added in 3.5
        Requirement(None, "3.9", "3.12")    # deprecated in 3.9, removed in 3.12

    """
    def __init__(self,
                 added: Optional[str] = None,
                 deprecated: Optional[str] = None,
                 removed: Optional[str] = None
                 ) -> None:
        """ Initialize feature requirement. """
        self.added = added
        self.deprecated = deprecated
        self.removed = removed

    def __lt__(self, other: object) -> bool:
        """ Less than "<" operator. Used for sorting requirements """
        if not isinstance(other, Requirement):
            raise TypeError(f'Expected a Requirement, received a '
                            f'{type(other).__name__}')

        # zip both instances and compare all 3 versions
        for version, other_ver in zip(self, other):
            if version_tuple(version) < version_tuple(other_ver):
                return True
            elif version_tuple(version) == version_tuple(other_ver):
                continue
            else:
                return False
        return False

    def __iter__(self):
        yield from (self.added, self.deprecated, self.removed)

    def __str__(self) -> str:
        return f'{self.added}, {self.deprecated}, {self.removed}'


class Changelog:
    """ A simple changelog dictionary loaded from json. """

    def __init__(self, filename: str) -> None:
        """ Initialize changelog from a json file.

        Args:
            filename (str): file path of the changelog.
        """
        with open(filename, 'r') as infile:
            self.changelog = json.load(infile)

    def get_requirement(self, name: str) -> Requirement:
        """ Returns a feature's version requirement.

        Args:
            name (str): name of the feature.

        Returns:
            Requirement: the feature requirement, or an empty Requirement.
        """
        return Requirement(**self.changelog.get(name, {}))

    def items(self):
        return self.changelog.items()


class Analyzer(ast.NodeVisitor):
    """ Parse abstract syntax tree and determine script requirements. """

    def __init__(self, filename: Path) -> None:
        """ Initialize node analyzer.

        Args:
            filename (Path): file path of the script.
        """
        self.filename = filename
        self.requirements = {}

        # Python versions are always internally stored as strings.
        # There is no way to store versions like "3.11.1" as a float.
        self.min_version = '3.0'

        # Load individual changelogs
        self.modules = Changelog('data/modules.json')
        self.exceptions = Changelog('data/exceptions.json')
        self.functions = Changelog('data/functions.json')

    def report_minversion(self) -> None:
        """ Print the minimum script requirement. """
        print(f'{self.filename}: requires {self.min_version}')

    def report(self) -> None:
        """ Print script requirements. """
        # TODO: generate a prettier report
        print()

        # Print minimum version
        self.report_minversion()

        # Sort by requirement then by feature name
        requirements = sorted(self.requirements.items(), key=lambda a: (a[1], a[0]))

        # Print requirements
        warnings = {}
        for feature, requirement in requirements:
            # Print added features
            if requirement.added:
                print(f'  {feature} requires {requirement.added}')

            # Build dictionary of deprecations and removals
            if requirement.deprecated or requirement.removed:
                warnings[feature] = requirement

        # Print warning about deprecated and removed features
        if warnings:
            print()
            print('Warning: Found deprecated or removed features:')
            for feature, changes in warnings.items():
                # Build description
                description = []
                if changes.deprecated:
                    description.append(f'deprecated in {changes.deprecated}')
                if changes.removed:
                    description.append(f'removed in {changes.removed}')
                print(f'  {feature} is {" and ".join(description)}')

    def visit_Import(self, node: ast.Import) -> None:
        """ Check import statements for module changes.

        Example:
            `import a, b, c`

        Args:
            node (ast.Import): an import statement.
        """
        for alias in node.names:
            self._check_module(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """ Check import from statements for module changes.

        Example:
            `from module import a, b, c`

        Args:
            node (ast.ImportFrom): an import from statement.
        """
        for alias in node.names:
            # Handle wildcard "from module import *"
            if alias.name == '*':
                self._check_module(node.module)
            else:
                self._check_module(node.module + '.' + alias.name)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """ Check attribute accesses for changes.

        Args:
            node (ast.Attribute): an attribute access.
        """
        self._check_attribute(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """ Check function calls for changes.

        Args:
            node (ast.Call): a function call.
        """
        if isinstance(node.func, ast.Name):
            self._check_function(node.func.id)
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        """ Check raised exceptions for new exceptions types.

        Args:
            node (ast.Raise): a raise statement.
        """
        if isinstance(node.exc, ast.Call):
            self._check_exception(node.exc.func.id)
        elif isinstance(node.exc, ast.Name):
            self._check_exception(node.exc.id)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """ Check caught exceptions for new exceptions types.

        Args:
            node (ast.ExceptHandler): a single except clause.
        """
        if isinstance(node.type, ast.Tuple):
            # Handle multiple exceptions grouped in a tuple
            # i.e: "except (TypeError, ValueError) as e:"
            for name in node.type.elts:
                self._check_exception(name.id)
        elif isinstance(node.type, ast.Name):
            self._check_exception(node.type.id)

        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        """ Check for unicode literals which were added in Python 3.3

        Args:
            node (ast.Constant): a constant value or literal.
        """
        if node.kind == 'u':
            self._update_requirements('unicode literal', Requirement('3.3'))
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """ Check for fstring literals which were added in Python 3.6

        Args:
            node (ast.JoinedStr): an fstring literal.
        """
        self._update_requirements('fstring literal', Requirement('3.6'))
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        """ Check for walrus operators which were added in Python 3.8

        Args:
            node (ast.NamedExpr): a named expression.
        """
        self._update_requirements('walrus operator', Requirement('3.8'))
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """ Check for match statements which were added in Python 3.10

        Args:
            node (ast.Match): a match statement.
        """
        self._update_requirements('match statement', Requirement('3.10'))
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """ Check for multiple context managers which were added in Python 3.1

        Example:
            `with open(file1, 'r') as infile, open(file2, 'w') as outfile:`

        Args:
            node (ast.With): a with block.
        """
        if len(node.items) > 1:
            self._update_requirements('multiple context managers', Requirement('3.1'))
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        """ Check for "yield from" expressions which were added in Python 3.3

        Args:
            node (ast.YieldFrom): a yield from expression.
        """
        self._update_requirements('yield from expression', Requirement('3.3'))
        self.generic_visit(node)

    def generic_visit(self, node: ast.AST) -> None:
        """ Generic node visitor. Handle nodes not covered by a specific visitor method.

        Args:
            node (ast.AST): an ast node, can be any node type.
        """
        # Check for async/await reserved keywords which were added in Python 3.7
        if isinstance(node, ast.AsyncFunctionDef | ast.AsyncFor | ast.AsyncWith | ast.Await):
            self._update_requirements('async and await', Requirement('3.7'))

        # Let the super class handle remaining nodes.
        # This must be called for child nodes to be traversed.
        super().generic_visit(node)

    def _update_requirements(self, name: str, requirement: Requirement) -> None:
        """ Update script requirements.

        Args:
            name (str): name of the feature.
            requirement (Requirement): the version requirement.
        Raises:
            TypeError: If the requirement is an invalid type.
        """
        if not isinstance(requirement, Requirement):
            raise TypeError(f'Unsupported type. Expected a Requirement,'
                            f' received a {type(requirement).__name__}')

        if name not in self.requirements.keys():
            # Update minimum version
            if version_tuple(requirement.added) > version_tuple(self.min_version):
                self.min_version = requirement.added
            # Update requirements
            self.requirements[name] = requirement

    def _check_exception(self, exception: str) -> None:
        """ Check for new exception types.

        Args:
            exception (str): name of the exception.
        """
        changes = self.exceptions.get_requirement(exception)
        if changes:
            self._update_requirements(exception, changes)

    def _check_function(self, function: str) -> None:
        """ Check for calls to new functions.

        Args:
            function (str): name of the function.
        """
        changes = self.functions.get_requirement(function)
        if changes:
            # Special case: join aiter/anext feature names
            if function in ('aiter', 'anext'):
                function = 'aiter and anext'
            self._update_requirements(function, changes)

    def _check_module(self, module: str) -> None:
        """ Check for module changes.

        Args:
            module (str): name of the module or attribute.
        """
        changes = self.modules.get_requirement(module)
        if changes:
            self._update_requirements(module, changes)

    def _check_attribute(self, node: ast.Attribute) -> None:
        """ Check for attribute changes.

        Args:
            node (ast.Attribute): an Attribute node, can be a nested Attribute.
        """
        # Check full attribute name
        self._check_module(self._get_attribute_name(node))

    def _get_attribute_name(self, node: ast.Name | ast.Attribute) -> str:
        """ Combine nested attribute name into a single string.

        Args:
            node (ast.Name | ast.Attribute): a Name or Attribute node.

        Returns:
            str: the full attribute string (i.e "self.modules.get_requirement")
        """
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
            the version string.

    Returns:
        tuple[int, int, int]:
            a tuple of (major, minor, micro) version numbers.
    """
    if not version:
        return tuple()
    return tuple(map(int, (version.split('.'))))


def detect_version(path: str | Path, quiet: bool = False) -> None:
    """Analyze a Python script (.py file) and print requirements.

    Args:
        path (str | Path): file path of the script.
        dump_ast (bool, optional): print ast to stdout. Defaults to False.
    """
    try:
        with open(path, 'r') as source:
            tree = ast.parse(source.read())

            analyzer = Analyzer(path)
            analyzer.visit(tree)

            if quiet:
                analyzer.report_minversion()
            else:
                analyzer.report()

    except SyntaxError:
        raise ValueError(f'Error reading {path}. Not a valid python 3 script.')


def detect_directory(path: str | Path, quiet: bool = False) -> None:
    """ Detect requirements of all python scripts in a directory.

    Args:
        path (str | Path): directory path.
        dump_ast (bool, optional): print ast to stdout. Defaults to False.

    Raises:
        ValueError: if the path is invalid.
    """
    path = Path(path)
    if not path.is_dir():
        raise ValueError('Error reading directory. Not a valid directory path.')

    script_files = list(path.rglob('[!.]*.py'))
    if not script_files:
        raise ValueError('Error reading directory. No python scripts found.')

    for script in script_files:
        detect_version(script, quiet)


def main():
    parser = argparse.ArgumentParser(
        description='Detect Python script requirements using abstract syntax trees.')

    parser.add_argument(
        'path',
        help='python script or a directory of scripts',
        type=Path)

    parser.add_argument(
        '-q', '--quiet',
        help="don't show details",
        action='store_true')

    args = parser.parse_args()

    try:
        if args.path.is_file():
            detect_version(args.path, args.quiet)
        elif args.path.is_dir():
            detect_directory(args.path, args.quiet)
        else:
            parser.error('Invalid path. Not a file or directory.')
    except OSError as e:
        raise SystemExit(f'Error reading {e.filename} ({e.strerror})')
    except ValueError as e:
        raise SystemExit(e)


if __name__ == '__main__':
    main()
