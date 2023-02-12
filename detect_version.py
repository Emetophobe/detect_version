#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import ast
import sys
import json
import argparse

from collections import defaultdict
from typing import Optional
from os import PathLike


# Action constants
ACTION_ADDED = 'added'
ACTION_DEPRECATED = 'deprecated'
ACTION_REMOVED = 'removed'
ALL_ACTIONS = (ACTION_ADDED, ACTION_DEPRECATED, ACTION_REMOVED)


# For type hinting. Optional [added, removed, deprecated] version strings.
VersionHistory = tuple[Optional[str], Optional[str], Optional[str]]


class Module:
    """ A module holds the version history (or changelog) of one of Python's built-in modules. """

    def __init__(self, changes: dict) -> None:
        """ Initialize built-in module from json dictionary. """
        # Copy dictionary to a defaultdict. Empty keys return an empty dictionary.
        self.changes = defaultdict(dict, changes)

        self.module_info = self.changes['module']
        self.attributes = self.changes['attributes']

    def get_module_requirements(self) -> Optional[VersionHistory]:
        """ Get module requirements as a Requirements namedtuple of
            optional versions (added, deprecated, removed).

        Returns:
            Optional[tuple]: _description_
        """
        return self._get_requirements(self.module_info)

    def get_attribute_requirements(self, attribute: str) -> Optional[VersionHistory]:
        """ Get attribute requirements as a 3-tuple of version changes (added, deprecated, removed).

        Args:
            attribute (str): Name of the attribute.

        Returns:
            Optional[tuple]: Tuple of attribute requirements.
        """
        return self._get_requirements(self.attributes.get(attribute, None))

    def _get_requirements(self, source: dict) -> Optional[VersionHistory]:
        """ Convert source dictionary into a tuple of version requirements.
            None is used for empty requirements. """
        if source:
            return VersionHistory(source.get(action, None) for action in ALL_ACTIONS)
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
        self.requirements = dict()

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
            feature (str): Name of the feature change.
            requirements (tuple or str): Tuple of

        Raises:
            TypeError: _description_
        """

        if not any(requirements):
            raise ValueError('Missing requirements')

        # Convert to string requirements to a tuple
        if isinstance(requirements, str):
            requirements = (requirements, None, None)
        elif not isinstance(requirements, tuple):
            raise TypeError(f'Unsupported type: expected one of (Requirements, tuple, str)'
                            f' Received a {type(requirements).__name__}')

        # Check if a feature is already added
        if feature in self.requirements.keys() and self.requirements[feature] == requirements:
            return

        # Update requirements
        self.update_version(requirements[0])
        self.requirements[feature] = requirements

    def update_version(self, version: str) -> None:
        """ Update minimum detected script version.

        Args:
            version (str): The version string.
        """
        if not version:
            return

        # Convert version strings to tuples for comparison
        if version_tuple(version) > version_tuple(self.min_version):
            self.min_version = version

    def visit_Import(self, node: ast.Import) -> None:
        """ Scan import statements for new modules.

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
        """ Scan "from x import a, b, c " statements for new modules or attributes.

            node.module is the module name (i.e "from x")
            node.names is the list of imports (i.e "import a, b, c")
        """
        if node.module in self.modules.keys():
            module = self.modules[node.module]

            for alias in node.names:
                if alias.name == '*':
                    # Handle wildcard import i.e 'from module import *'
                    name = node.module
                    requirements = module.get_module_requirements()
                else:
                    # Check for matching attribute
                    name = f'{node.module}.{alias.name}'
                    requirements = module.get_attribute_requirements(alias.name)

                if requirements:
                    self.update_requirements(name, requirements)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """ Check for attribute accesses for module changes.

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
        """ Check function calls for version changes.

            node.func is the function (which can be a Name or Attribute node).
        """
        if isinstance(node.func, ast.Name):
            for function, version in self.functions.items():
                if node.func.id == function:
                    self.update_requirements(f'{function} function', version)

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
            node.value: The actual Python object the constant represents.
            node.kind: "u" for unicode string, None otherwise.
        """
        if node.kind == 'u':
            self.update_requirements('unicode literals', '3.3')
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AST):
        """ Check for async/await coroutines which were added in Python 3.5 """
        self.update_requirements('async/await coroutines', '3.5')
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """ Check for formatted string literals (f-strings) which were added in Python 3.6 """
        self.update_requirements('fstring literals', '3.6')
        self.generic_visit(node)

    # Use same method for all async/await visitors
    visit_AsyncFor = visit_AsyncWith = visit_Await = visit_AsyncFunctionDef

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        """ Check for walrus operators which were added in Python 3.8 """
        self.update_requirements('walrus operators', '3.8')
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """ Check for match/case statements which were added in Python 3.10 """
        self.update_requirements('match statements', '3.10')
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """ Check for multiple context managers which was added in Python 3.1 """
        if len(node.items) > 1:
            self.update_requirements('multiple with clauses', '3.1')
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        """ Check for "yield from" statement which was added in Python 3.3 """
        self.update_requirements('yield from expression', '3.3')
        self.generic_visit(node)

    def _check_function(self, name: str) -> None:
        """ Check for new functions. """
        for action, history in self.functions.items():
            for version, attributes in history.items():
                if name in attributes:
                    self.update_requirements(name, version)

    def _check_exception(self, name: str) -> None:
        """ Check for new exception types.

        Args:
            name (str): Name of the exception; i.e "RecursionError"
        """
        if name in self.exceptions.keys():
            self.update_requirements(name, self.exceptions[name])

    def _check_attribute(self, name: str, attribute: str) -> None:
        """ Check for new module attributes.

        Args:
            name (str): The name of the module.
            attribute (str): The name of the attribute.
        """
        # Find matching module
        if name in self.modules.keys():
            module = self.modules[name]

            # Update requirements if we found a matching attribute
            requirements = module.get_attribute_requirements(attribute)
            if requirements:
                self.update_requirements(f'{name}.{attribute}', requirements)


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
    """ Load modules history and convert to a dictionary of Modules. """
    modules = {}
    for name, changelog in load_changes(filename).items():
        modules[name] = Module(changelog)
    return modules


def version_tuple(version: str) -> tuple[int, int, int]:
    """ Split a version string into a tuple; i.e "3.11.1" -> (3, 11, 1) """
    if not version:
        return None
    return tuple(map(int, (version.split('.'))))


def dump_file(path: PathLike) -> None:
    """ Debugging functions. Parse script file and print ast to stdout. """
    with open(path, 'r') as source:
        dump_node(ast.parse(source.read()))


def dump_node(node: ast.AST) -> None:
    """  Debugging functions. Print ast node to stdout. """
    print(ast.dump(node, indent=4))


def dump_json(data: dict) -> None:
    """  Debugging functions. Print json to stdout. """
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
