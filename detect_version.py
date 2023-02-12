#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import ast
import sys
import json
import argparse

from collections import defaultdict
from typing import Optional
from os import PathLike


# Version constants
VERSION_ADDED = 'added'
VERSION_DEPRECATED = 'deprecated'
VERSION_REMOVED = 'removed'
ALL_VERSIONS = (VERSION_ADDED, VERSION_DEPRECATED, VERSION_REMOVED)


# For type hinting. Tuple of Optional (added, removed, deprecated) version strings.
VersionHistory = tuple[Optional[str], Optional[str], Optional[str]]


class Module:
    """ A module holds the version history (or changelog) of one of Python's built-in modules.

        Each module has two main attributes:
            module: Version information about the module itself.
            attributes: Version information about the module's functions, exceptions, etc..

        Requirements are returned as a tuple of 3 version strings (added, removed, deprecated).
        Each module or attribute will have one, two, or all three of the version strings.
        None is used for empty values, i.e:

            (None, "3.11", "3.9")
            ("3.5", "3.9", None)
    """

    def __init__(self, changes: dict) -> None:
        """ Initialize built-in module from json dictionary. """
        # Copy dictionary to a defaultdict. Empty keys return an empty dictionary.
        self.changes = defaultdict(dict, changes)

        self.module_info = self.changes['module']
        self.attributes = self.changes['attributes']

    def get_module_requirements(self) -> Optional[VersionHistory]:
        """ Get module requirements as a 3-tuple of version changes.

        Returns:
            Optional[VersionHistory]: The module changelog or None.
        """
        return self._get_requirements(self.module_info)

    def get_attribute_requirements(self, attribute: str) -> Optional[VersionHistory]:
        """ Get attribute requirements as a 3-tuple of version changes.

        Args:
            attribute (str): Name of the attribute.

        Returns:
            Optional[VersionHistory]: The attribute changelog or None.
        """
        return self._get_requirements(self.attributes.get(attribute, None))

    def _get_requirements(self, source: dict) -> Optional[VersionHistory]:
        """ Convert source dictionary into a tuple of version requirements.

        Args:
            source (dict): A module info or attribute dictionary.

        Returns:
            A 3-tuple of the added, deprecated, and removed versions.
        """
        if source:
            return VersionHistory(source.get(action, None) for action in ALL_VERSIONS)
        return None


class Analyzer(ast.NodeVisitor):
    """ Analyzer is used to parse abstract syntax tree (ast) and determine
        a minimum Python version. TODO: more info
    """

    def __init__(self, path: PathLike) -> None:
        """ Initialize node analyzer.

        Args:
            path (PathLike): filename of the script.
        """
        self.script = path
        self.min_version = '3.0'
        self.requirements = {}

        self.modules = load_modules('modules.json')
        self.functions = load_changes('functions.json')
        self.exceptions = load_changes('exceptions.json')

    def report(self) -> None:
        """ Print script requirements. """
        # requirements = sorted(self.requirements.items(),
        #                      key=lambda kv: (requirement_tuple(kv[1]), kv[0]))

        warnings = {}

        # Print minimum detected script version and detailed requirements
        print(f'{self.script}: requires {self.min_version}')
        for feature, version in self.requirements.items():
            added, deprecated, removed = version

            if added:
                print(f'  {feature} requires {added}')

            if deprecated or removed:
                warnings[feature] = version

        # Print warning about deprecations and removals
        if warnings:
            print()
            print('Warning: Found deprecated or removed features:')
            for feature, version in warnings.items():
                _, deprecated, removed = version
                if deprecated:
                    print(f'  {feature} deprecated in version {deprecated}')
                if removed:
                    print(f'  {feature} removed in version {removed}')

    def update_requirements(self, feature: str, requirements: tuple | str) -> None:
        """ Update script requirements.

        Args:
            feature (str): Name of the feature.
            requirements (tuple or str): Tuple of version requirements.

        Raises:
            ValueError: If the requirements are missing.
            TypeError:  If the requirements are an invalid type.
        """

        if not any(requirements):
            raise ValueError('Missing requirements')

        # Convert to string requirements to a tuple
        if isinstance(requirements, str):
            requirements = (requirements, None, None)
        elif not isinstance(requirements, tuple):
            raise TypeError(f'Unsupported type: expected a tuple or str, '
                            f'received a {type(requirements).__name__}')

        # Check if a feature is already added
        if feature in self.requirements.keys() and self.requirements[feature] == requirements:
            return

        # Update requirements
        self.update_version(requirements[0])
        self.requirements[feature] = requirements

    def update_version(self, version: str) -> None:
        """ Update script version.

        Args:
            version (str): The version string.
        """
        if not version:
            return

        # Convert version strings to tuples for comparison
        if version_tuple(version) > version_tuple(self.min_version):
            self.min_version = version

    def visit_Import(self, node: ast.Import) -> None:
        """ Scan import statements for module changes.

            node.names is the list of imports (i.e "import a, b, c")
        """
        for alias in node.names:
            if alias.name in self.modules.keys():
                module = self.modules[alias.name]
                requirements = module.get_module_requirements()
                if requirements:
                    self.update_requirements(f'{alias.name} module', requirements)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """ Scan "from x import a, b, c" import statements for module changes.

            node.module is the module name (i.e "from x")
            node.names is the list of imports (i.e "import a, b, c")
        """
        if node.module in self.modules.keys():
            module = self.modules[node.module]

            for alias in node.names:
                if alias.name == '*':
                    # Handle wildcard import i.e 'from module import *'
                    name = f'{node.module} module'
                    requirements = module.get_module_requirements()
                else:
                    # Check for matching attribute
                    name = f'{node.module}.{alias.name}'
                    requirements = module.get_attribute_requirements(alias.name)

                if requirements:
                    self.update_requirements(name, requirements)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """ Check for module attribute changes.

            node.value is a node that can be a Name or an Attribute.
            node.attr is a string of the attribute name.
            node.ctx is the context of the attribute access (Load, Store or Del).
        """
        if isinstance(node.value, ast.Name):
            self._check_attribute(node.value.id, node.attr)
        elif isinstance(node.value, ast.Attribute):
            self._check_attribute(node.value.value, node.attr)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """ Check for function changes.

            node.func is the function (which can be a Name or Attribute node).
        """
        if isinstance(node.func, ast.Name):
            for function, changes in self.functions.items():
                if node.func.id == function:
                    # Special case: Combine aiter/anext functions for display
                    if function in ('aiter', 'anext'):
                        self.update_requirements('aiter and anext', changes[VERSION_ADDED])
                    else:
                        self.update_requirements(f'{function} function', changes[VERSION_ADDED])

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
            self.update_requirements('unicode literals', '3.3')
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
        self.update_requirements('async and await', '3.7')
        self.generic_visit(node)

    # Use same method for all async/await visitors
    visit_AsyncFor = visit_AsyncWith = visit_Await = visit_AsyncFunctionDef

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """ Check for fstring literals which were added in Python 3.6 """
        self.update_requirements('fstring literals', '3.6')
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        """ Check for walrus operators which were added in Python 3.8 """
        self.update_requirements('walrus operators', '3.8')
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """ Check for match/case statements which were added in Python 3.10 """
        self.update_requirements('match statements', '3.10')
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """ Check for multiple context managers which were added in Python 3.1 """
        if len(node.items) > 1:
            self.update_requirements('multiple with clauses', '3.1')
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        """ Check for "yield from" expressions which were added in Python 3.3 """
        self.update_requirements('yield from expression', '3.3')
        self.generic_visit(node)

    def _check_exception(self, name: str) -> None:
        """ Check for new exception types. """
        if name in self.exceptions.keys():
            self.update_requirements(name, self.exceptions[name])

    def _check_attribute(self, module: str, attribute: str) -> None:
        """ Check for new module attributes. """
        # Find matching module and update requirements
        if module in self.modules.keys():
            requirements = self.modules[module].get_attribute_requirements(attribute)
            if requirements:
                self.update_requirements(f'{module}.{attribute}', requirements)


def detect_version(path: PathLike) -> None:
    """ Detect minimum version required to run a script. """
    with open(path, 'r') as source:
        tree = ast.parse(source.read())

    analyzer = Analyzer(path)
    analyzer.visit(tree)
    analyzer.report()


def load_changes(filename: PathLike) -> dict:
    """ Load dictionary of changes from a json file. """
    with open(filename, 'r', encoding='utf-8') as infile:
        return json.load(infile)


def load_modules(filename: PathLike) -> dict[str, Module]:
    """ Load modules changelog and convert to a dictionary of Modules. """
    modules = {}
    for name, changelog in load_changes(filename).items():
        modules[name] = Module(changelog)
    return modules


def version_tuple(version: str) -> tuple[int, int, int]:
    """ Split a version string into a tuple of ints;
        Example: "3.11.1" turns into (3, 11, 1)
    """
    if not version:
        return None
    return tuple(map(int, (version.split('.'))))


def dump_file(path: PathLike) -> None:
    """ Parse script file and print ast to stdout. """
    with open(path, 'r') as source:
        dump_node(ast.parse(source.read()))


def dump_node(node: ast.AST) -> None:
    """  Print ast node to stdout. """
    print(ast.dump(node, indent=4))


def dump_json(data: dict) -> None:
    """  Print json to stdout. """
    print(json.dumps(data, indent=4))


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
    except TypeError as e:
        print(e)
    except ValueError as e:
        print(e)


if __name__ == '__main__':
    main()
