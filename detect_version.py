#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import ast
import sys
import json
import argparse


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


class Analyzer(ast.NodeVisitor):
    """ Node Visitor used to walk the abstract syntax tree. """

    def __init__(self):
        self.min_version = PYTHON3
        self.requirements = set()
        self.changes = load_changes()

    def report(self, path):
        """ Print version report. """
        print(f'{path}: requires {self.min_version}')
        for requirement in self.requirements:
            print(f'  {requirement}')

    def update_requirements(self, feature, version):
        """ Update script requirements. """
        self.requirements.add(f'{feature} requires {version}')
        self.min_version = max(self.min_version, version)

    def generic_visit(self, node: ast.AST):
        """ Check ast node types not covered by a specific visitor method. """
        if isinstance(node, (ast.AsyncFunctionDef, ast.AsyncFor, ast.AsyncWith, ast.Await)):
            # Check for async/await which were added in Python 3.5
            self.update_requirements('async/await coroutines', PYTHON35)
        super().generic_visit(node)

    def visit_Import(self, node: ast.Import):
        """ Scan import statements for specific modules. """
        for version, module, additions in self.get_changes():
            for alias in node.names:
                if module == alias.name and not additions:
                    self.update_requirements(f'{module} module', version)
                elif alias.name in additions:
                    self.update_requirements(f'{module}.{alias.name}', version)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """ Scan import from statements for specific modules. """
        for version, module, additions in self.get_changes():
            if node.module == module:
                for alias in node.names:
                    if alias.name in additions:
                        self.update_requirements(f'{module}.{alias.name}', version)
                    elif not additions and alias.name == '*':  # handle from module import *
                        self.update_requirements(f'{module} module', version)

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        """ Check attribute accesses for API changes. """
        if isinstance(node.value, ast.Name):
            self._check_attribute(node.value.id, node.attr)
        elif isinstance(node.value, ast.Attribute):
            self._check_attribute(node.value.value, node.attr)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """ Check function calls for API changes. """
        if isinstance(node.func, ast.Name):
            if node.func.id == 'callable':
                self.update_requirements('callable function', PYTHON32)
            if node.func.id == 'breakpoint':
                self.update_requirements('breakpoint function', PYTHON37)
            elif node.func.id in ('aiter', 'anext'):
                self.update_requirements('aiter/anext function', PYTHON310)

        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise):
        """ Check raised exceptions for new exceptions types. """
        self._check_exception(node.exc.id)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """ Check caught exceptions for new exceptions types."""
        self._check_exception(node.type.id)
        self.generic_visit(node)

    def visit_Str(self, node: ast.Str):
        """ Check for unicode literals i.e: u'this is a unicode literal' """
        if node.kind == 'u':
            self.update_requirements('unicode literal', PYTHON33)
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr):
        """ Check for fstrings which were added in Python 3.6 """
        self.update_requirements('fstring', PYTHON36)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match):
        """ Check for match/case statements which were added in Python 3.10 """
        self.update_requirements('match statement', PYTHON310)
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        """ Check for multiple context managers which was added in Python 3.1 """
        if len(node.items) > 1:
            self.update_requirements('multiple with clauses', PYTHON31)
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom):
        """ Check for "yield from" statement which was added in Python 3.3 """
        self.update_requirements('yield from statement', PYTHON33)
        self.generic_visit(node)

    def get_changes(self):
        """ Convenience method to yield tuples of module changes. """
        for version, changes in self.changes.items():
            for module, additions in changes.items():
                yield version, module, additions

    def _check_exception(self, name):
        """ Check for new exception classes. """
        if name == 'RecursionError':
            self.update_requirements('RecursionError exception', PYTHON35)
        elif name == 'ModuleNotFoundError':
            self.update_requirements('ModuleNotFoundError exception', PYTHON36)

    def _check_attribute(self, name, attr):
        """ Check for module additions. """
        for version, module, additions in self.get_changes():
            if name == module and attr in additions:
                self.update_requirements(f'{name}.{attr}', version)


def detect_version(path: str) -> None:
    """ Detect minimum version required to run a script. """
    with open(path, 'r') as source:
        tree = ast.parse(source.read())

    analyzer = Analyzer()
    analyzer.visit(tree)
    analyzer.report(path)


def load_changes():
    """ Load the dictionary of changes from file. """
    with open('changes.json', 'r', encoding='utf-8') as infile:
        return json.load(infile)


def dump_ast(path: str) -> None:
    """ Print ast to stdout. """
    with open(path, 'r') as source:
        tree = ast.parse(source.read())
        print(ast.dump(tree, indent=4))


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
