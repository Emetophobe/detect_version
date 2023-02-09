#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import ast
import sys
import json
import argparse

from os import PathLike


# Major Python releases
PYTHON3 = 'Python 3.0'
PYTHON31 = 'Python 3.1'
PYTHON32 = 'Python 3.2'
PYTHON33 = 'Python 3.3'
PYTHON34 = 'Python 3.4'
PYTHON35 = 'Python 3.5'
PYTHON36 = 'Python 3.6'
PYTHON37 = 'Python 3.7'
PYTHON38 = 'Python 3.8'
PYTHON39 = 'Python 3.9'
PYTHON310 = 'Python 3.10'
PYTHON311 = 'Python 3.11'
PYTHON312 = 'Python 3.12'


class Module:
    def __init__(self, module_name: str, changes: dict) -> None:
        self.name = module_name

        self.module_created = changes.get('module_created', None)
        self.module_deprecated = changes.get('module_deprecated', None)
        self.module_removed = changes.get('module_removed', None)

        self.added = changes.get('added', dict())
        self.deprecated = changes.get('deprecated', dict())
        self.removed = changes.get('removed', dict())

    def __str__(self):
        return self.module_name


class Analyzer(ast.NodeVisitor):
    """ Node Visitor used to walk the abstract syntax tree. """

    def __init__(self, path: PathLike) -> None:
        """ Initialize node analyzer.

        Args:
            path (PathLike): filename of the script to parse.
        """
        self.script = path
        self.min_version = PYTHON3
        self.requirements = {}

        self.modules = load_modules('modules.json')
        self.exceptions = load_changes('exceptions.json')
        self.functions = load_changes('functions.json')

    def report(self) -> None:
        """ Print version report. """
        print(f'{self.script}: requires {self.min_version}')

        requirements = sorted(self.requirements.items(),
                              key=lambda kv: (version_tuple(kv[1]), kv[0]),
                              reverse=False)
        for feature, version in requirements:
            print(f'  {feature} requires {version}')

    def update_requirements(self, feature: str, version: str) -> None:
        """ Update minimum requirements and version.

            Args:
                feature (str): Name of the feature
                version (str): Initial Python version
        """
        self.requirements[feature] = version
        if version_tuple(version) > version_tuple(self.min_version):
            self.min_version = version

    def visit_Import(self, node: ast.Import) -> None:
        """ Scan import statements for new modules.

            node.names is the list of imports.
        """
        for alias in node.names:
            for module in self.modules:
                if alias.name == module.name and module.module_created:
                    self.update_requirements(module.name, module.module_created)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """ Scan "from x import a, b, c " statements for new modules or attributes.

            node.module is the module name in the "from x" part of the statement
            node.names is the list of imports in the "import a, b, c" part of the statement
        """
        for module in self.modules:
            if node.module != module.name:
                continue

            for alias in node.names:
                # Handle wildcard cases i.e 'from module import *'
                if alias.name == '*':
                    self.update_requirements(module.name, module.module_created)
                    continue

                # Check for matching attribute
                for version, attributes in module.added.items():
                    if alias.name in attributes:
                        self.update_requirements(f'{module.name}.{alias.name}', version)

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """ Check for attribute accesses for module changes.

            node.value is a node, typically a Name or an Attribute itself.
            node.attr is a string giving the name of the attribute.
            node.ctx is the context of the attribute access (Load, Store or Del).
        """
        if isinstance(node.value, ast.Name):
            self._check_attribute(node.value.id, node.attr)
        elif isinstance(node.value, ast.Attribute):
            self._check_attribute(node.value.value, node.attr)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """ Check function calls for module changes.

            node.func is the function (which can be a Name or Attribute node).
        """
        if isinstance(node.func, ast.Name):
            for function, version in self.functions.items():
                if isinstance(function, tuple):  # tuple of function names
                    if node.func.id in function:
                        functions = '/'.join(function)  # combine function names
                        self.update_requirements(functions, version)
                elif isinstance(function, str):  # single function name
                    if node.func.id == function:
                        self.update_requirements(function, version)

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
            self.update_requirements('unicode literal', PYTHON33)
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """ Check for formatted strings (fstrings) which were added in Python 3.6. """
        self.update_requirements('fstring', PYTHON36)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AST):
        """ Check for async/await coroutines which were added in Python 3.5. """
        self.update_requirements('async/await', PYTHON35)
        self.generic_visit(node)

    # Use same method for all async/await visitors
    visit_AsyncFor = visit_AsyncWith = visit_Await = visit_AsyncFunctionDef

    def visit_Match(self, node: ast.Match) -> None:
        """ Check for match/case statements which were added in Python 3.10 """
        self.update_requirements('match statement', PYTHON310)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """ Check for multiple context managers which was added in Python 3.1 """
        if len(node.items) > 1:
            self.update_requirements('multiple with clauses', PYTHON31)
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        """ Check for "yield from" statement which was added in Python 3.3 """
        self.update_requirements('yield from statement', PYTHON33)
        self.generic_visit(node)

    def _check_attribute(self, name: str, attr: str) -> None:
        """ Check for calls to new module attributes. """
        for module in self.modules:
            if name == module.name:
                for version, attributes in module.added.items():
                    if attr in attributes:
                        self.update_requirements(f'{name}.{attr}', version)
                        return

    def _check_exception(self, name: str) -> None:
        """ Check for new exception classes. """
        for exception, version in self.exceptions.items():
            if name == exception:
                self.update_requirements(exception, version)
                return


def detect_version(path: PathLike) -> None:
    """ Detect minimum version required to run a script. """
    with open(path, 'r') as source:
        tree = ast.parse(source.read())

    analyzer = Analyzer(path)
    analyzer.visit(tree)
    analyzer.report()


def load_changes(filename: PathLike) -> dict:
    """ Load changes from a json file. """
    with open(filename, 'r', encoding='utf-8') as infile:
        return json.load(infile)


def load_modules(filename: PathLike) -> list[Module]:
    """ Read modules dictionary and convert to a list of Modules. """
    modules = load_changes('modules.json')
    return [Module(name, changes) for name, changes in modules.items()]


def dump_file(path: PathLike) -> None:
    """ Parse script file and print ast to stdout. """
    with open(path, 'r') as source:
        dump_node(ast.parse(source.read()))


def dump_node(node: ast.AST) -> None:
    """ Print ast node to stdout. """
    print(ast.dump(node, indent=4))


def version_tuple(version: str) -> tuple:
    """ Split a version string into a tuple; i.e "3.11.1" -> (3, 11, 1) """
    version = version.removeprefix('Python ')
    return tuple(map(int, (version.split('.'))))


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
