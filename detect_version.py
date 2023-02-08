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


# Changes to built-in exceptions
EXCEPTION_CHANGES = (
    ('ResourceWarning', PYTHON32),
    ('TimeoutError', PYTHON33),
    ('RecursionError', PYTHON35),
    ('StopAsyncIteration', PYTHON35),
    ('ModuleNotFoundError', PYTHON36),
    ('EncodingWarning', PYTHON310),
    ('ExceptionGroup', PYTHON311),
)


# Changes to built-in functions
FUNCTION_CHANGES = (
    ('callable', PYTHON32),
    ('breakpoint', PYTHON37),
    (('aiter', 'anext'), PYTHON310)
)


class Module:
    def __init__(self, name: str, data: dict) -> None:
        self.name = name
        self.created = data.get('created', None)
        self.added = data.get('added', dict())

        if not self.created and not self.added:
            raise ValueError(f'Invalid module {name} (missing changes)')

    def __str__(self):
        return self.name


class Analyzer(ast.NodeVisitor):
    """ Node Visitor used to walk the abstract syntax tree. """

    def __init__(self) -> None:
        self.modules = load_changes('modules.json')
        self.min_version = PYTHON3
        self.requirements = {}

    def report(self, path: PathLike) -> None:
        """ Print version report. """
        print(f'{path}: requires {self.min_version}')

        requirements = sorted(self.requirements.items(),
                              key=lambda kv: (version_tuple(kv[1]), kv[0]),
                              reverse=False)
        for feature, version in requirements:
            print(f'  {feature} requires {version}')

    def update_requirements(self, feature: str, version: str) -> None:
        """ Update script requirements and minimum version. """
        self.requirements[feature] = version
        if version_tuple(version) > version_tuple(self.min_version):
            self.min_version = version

    def visit_Import(self, node: ast.Import) -> None:
        """ Scan import statements for new modules. """
        for alias in node.names:
            for module in self.modules:
                if alias.name == module.name and module.created:
                    self.update_requirements(module.name, module.created)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """ Scan "from ... import" statements for new modules or attributes."""
        for module in self.modules:
            if node.module != module.name:
                continue

            for alias in node.names:
                # Handle wildcard cases i.e 'from module import *'
                if alias.name == '*':
                    self.update_requirements(module.name, module.created)
                    continue

                # Check for matching attribute
                for version, attributes in module.added.items():
                    if alias.name in attributes:
                        self.update_requirements(f'{module.name}.{alias.name}', version)

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """ Check for attribute accesses for module changes. """
        if isinstance(node.value, ast.Name):
            self._check_attribute(node.value.id, node.attr)
        elif isinstance(node.value, ast.Attribute):
            self._check_attribute(node.value.value, node.attr)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """ Check function calls for module changes. """
        if isinstance(node.func, ast.Name):
            for function, version in FUNCTION_CHANGES:
                if isinstance(function, tuple):  # tuple of function names
                    if node.func.id in function:
                        functions = '/'.join(function)  # combine function names
                        self.update_requirements(functions, version)
                elif isinstance(function, str):  # single function name
                    if node.func.id == function:
                        self.update_requirements(function, version)

        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        """ Check raised exceptions for new exceptions types. """
        if isinstance(node.exc, ast.Call):
            self._check_exception(node.exc.func.id)
        elif isinstance(node.exc, ast.Name):
            self._check_exception(node.exc.id)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """ Check caught exceptions for new exceptions types."""
        self._check_exception(node.type.id)
        self.generic_visit(node)

    def visit_Str(self, node: ast.Str) -> None:
        """ Check for unicode literals i.e: u'this is a unicode literal' """
        if node.kind == 'u':
            self.update_requirements('unicode literal', PYTHON33)
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """ Check for fstrings which were added in Python 3.6 """
        self.update_requirements('fstring', PYTHON36)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AST):
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
                break

    def _check_exception(self, name: str) -> None:
        """ Check for new exception classes. """
        for exception, version in EXCEPTION_CHANGES:
            if name == exception:
                self.update_requirements(exception, version)
                break


def detect_version(path: PathLike) -> None:
    """ Detect minimum version required to run a script. """
    with open(path, 'r') as source:
        tree = ast.parse(source.read())

    analyzer = Analyzer()
    analyzer.visit(tree)
    analyzer.report(path)


def dump_ast(path: PathLike) -> ast.AST:
    """ Print ast to stdout. """
    with open(path, 'r') as source:
        tree = ast.parse(source.read())
    print(ast.dump(tree, indent=4))


def load_changes(filename: PathLike) -> list[Module]:
    """ Load module changes from file. """
    with open(filename, 'r', encoding='utf-8') as infile:
        data = json.load(infile)

    modules = []
    for module, changes in data.items():
        modules.append(Module(module, changes))
    return modules


def version_tuple(version: str) -> tuple:
    """ Split a version string "3.11.1" into a tuple (3, 11, 1) """
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
            dump_ast(args.path)
        else:
            detect_version(args.path)
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)


if __name__ == '__main__':
    main()
