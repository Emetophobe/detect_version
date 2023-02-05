#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import os
import sys
import ast
import argparse

# Major release numbers
PYTHON3 = (3, 0, 0)
PYTHON31 = (3, 1, 0)
PYTHON32 = (3, 2, 0)
PYTHON33 = (3, 3, 0)
PYTHON34 = (3, 4, 0)
PYTHON35 = (3, 5, 0)
PYTHON36 = (3, 6, 0)
PYTHON37 = (3, 7, 0)
PYTHON38 = (3, 8, 0)
PYTHON39 = (3, 9, 0)
PYTHON310 = (3, 10, 0)
PYTHON311 = (3, 11, 0)


# Module additions across different Python versions
MODULE_CHANGES = {
    # Python 3.1
    PYTHON31: {
        'collection': ['counter'],
        'importlib': []
    },

    # Python 3.2
    PYTHON32: {
        'abc': ['abstractclassmethod', 'abstractstaticmethod'],
        'argparse': [],
        'concurrent': ['futures'],
        'contextlib': ['ContextDecorator'],
        'datetime': ['timezone'],
        'functools': ['lru_cache'],
        'gzip': ['compress', 'decompress'],
        'hashlib': ['algorithms_available', 'algorithms_guaranteed'],
        'html': ['escape'],
        'itertools': ['accumulate'],
        'math': ['isfinite', 'expm1', 'erf', 'erfc', 'gamma', 'lgamma'],
        'os': ['environb', 'fscencode', 'fsdecode', 'getenvb',
               'get_exec_path', 'supports_bytes_environ'],
        'reprlib': ['recursive_repr'],
        'shutil': ['make_archive', 'unpack_archive'],
        'socket': ['detach'],
        'ssl': ['SSLContext', 'match_hostname', 'OPENSSL_VERSION',
                'OPENSSL_VERSION_INFO', 'OPENSSL_VERSION_NUMBER'],
        'sysconfig': [],
        'threading': ['Barrier'],
    },

    # Python 3.3
    PYTHON33: {
        'collections.abc': ['abc', 'ChainMap'],
        'faulthandler': [],
        'ipaddress': [],
        'inspect': ['signature', 'Signature', 'Parameter', 'BoundArguments'],
        'lzma': [],
        'math': ['log2'],
        'select': ['devpoll'],
        'sys': ['implementation'],
        'typing': ['SimpleNamespace'],
        'unittest': ['mock'],
        'venv': []
    },

    # Python 3.4
    PYTHON34: {
        'abc': ['ABC', 'get_cache_token'],
        'audioop': ['byteswap'],
        'asyncio': [],
        'contextlib': ['redirect_stdout, suppress'],
        'dis': ['Instruction', 'get_instruction', 'stack_effect'],
        'email': ['as_bytes'],
        'ensurepip': [],
        'enum': [],
        'filecmp': ['clear_cache', 'DEFAULT_IGNORES'],
        'functools': ['partialmethod', 'singledispatch'],
        'gc': ['get_stats'],
        'glob': ['escape'],
        'hashlib': ['pbkdf2_hmac'],
        'html': ['unescape'],
        'importlib': ['reload'],
        'inspect': ['unwrap'],
        'operator': ['length_hint'],
        'os': ['cpu_count', 'get_inheritable', 'set_inheritable',
               'get_handle_inheritable', 'set_handle_inheritable'],
        'pathlib': [],
        'plistlib': ['load', 'loads', 'dump', 'dumps'],
        're': ['fullmatch'],
        'resource': ['prlimit'],
        'selectors': [],
        'ssl': ['create_default_context', "get_default_verify_paths",
                'enum_certificates', 'enum_crls'],
        'stats': ['S_IFDOOR', 'S_IFPORT', 'S_IFWHT'],
        'statistics': [],
        'struct': ['iter_unpack'],
        'sys': ['getallocatedblocks'],
        'traceback': ['clear_frames'],
        'tracemalloc': [],
        'types': ['DynamicClassAttribute'],
        'weakref': ['WeakMethod', 'finalize'],
        'xml.etree.ElementTree': ['XMLPullParser'],
    },

    # Python 3.5
    PYTHON35: {
        'contextlib': ['redirect_stderr'],
        'os': ['scandir'],
        'subprocess': ['run'],
        'traceback': ['walk_stack', 'walk_tb', 'TracebackException',
                      'StackSummary', 'FrameSummary'],
        'types': ['coroutine', 'CoroutineType'],
        'urllib.request': ['HTTPPasswordMgrWithPriorAuth'],
    },

    # Python 3.6
    PYTHON36: {
        'os': ['fspath', 'PathLike'],
        'secrets': [],
    },

    # Python 3.7
    PYTHON37: {

    },

    # Python 3.8
    PYTHON38: {

    },

    # Python 3.9
    PYTHON39: {

    },

    # Python 3.10
    PYTHON310: {

    },

    # Python 3.11
    PYTHON311: {
        'hashlib': ['file_digest'],
        'tomllib': [],
    },
}


class Analyzer(ast.NodeVisitor):
    def __init__(self):
        self._min_version = PYTHON3

    def generic_visit(self, node):
        #print(type(node).__name__)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # Async function was added in Python 3.5
        print_requirement('async function', PYTHON35)
        self.min_version = PYTHON35

    def visit_AsyncFor(self, node: ast.AsyncFor):
        # Async for loop was added in Python 3.5
        print_requirement('async for loop', PYTHON35)
        self.min_version = PYTHON35

    def visit_Import(self, node: ast.Import):
        """ Scan import statement for specific modules. """
        for alias in node.names:
            for version, changes in MODULE_CHANGES.items():
                for module, additions in changes.items():
                    if module == alias.name and not additions:
                        print_requirement(f'{module} module', version)
                        self.min_version = version
                    elif alias.name in additions:
                        print_requirement(f'{module}.{alias.name}', version)
                        self.min_version = version

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """ Scan from ... import ... statement for specific modules. """
        for alias in node.names:
            for version, changes in MODULE_CHANGES.items():
                for module, additions in changes.items():
                    if node.module == module and alias.name in additions:
                        print_requirement(f'{module}.{alias.name}', version)
                        self.min_version = version

        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        # Assigned expression aka walrus operator was added in Python 3.8
        if isinstance(node.test, ast.NamedExpr):
            print_requirement('assignment expression', PYTHON38)
            self.min_version = PYTHON38

        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp):
        # print(f'visit_IfExp: {node.test=}')
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr):
        """ Scan for fstrings which were added in Python 3.6 """
        print_requirement('fstring', PYTHON36)
        self.min_version = PYTHON36
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        #print('visit_Call', node.func, node.args)

        if isinstance(node.func, ast.Name):
            print('Name:', node.func.id)
        elif isinstance(node.func, ast.Attribute):
            #print('visit_Call attribute:', node.func.value.id, node.func.attr)
            pass

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        self.check_attribute(node)
        self.generic_visit(node)

    def check_attribute(self, node: ast.Attribute):
        for version, changes in MODULE_CHANGES.items():
            for module, additions in changes.items():
                if node.value.id == module and node.attr in additions:
                    print_requirement(f'{node.value.id}.{node.attr}', version)
                    self.min_version = version

    def visit_Expr(self, node: ast.Expr):
        #print('visit_Expr', node.value)
        self.generic_visit(node)

    def visit_Expression(self, node: ast.Expression):
        #print('visit_Expression', node.body)
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        """ Support for multiple with statements was added in Python 3.1 """
        if len(node.items) > 1:
            print_requirement('multiple "with" clauses', PYTHON31)
            self.min_version = PYTHON31
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom):
        """ Scan for "yield from" statements which were added in Python 3.3 """
        print_requirement('"yield from" statement', PYTHON33)
        self.min_version = PYTHON33
        self.generic_visit(node)

    def visit_Str(self, node: ast.Str):
        if node.kind == 'u':
            # Explicit unicode literals were added in Python 3.3
            print_requirement('unicode literal', PYTHON33)
            self.min_version = PYTHON33
        self.generic_visit(node)

    @property
    def min_version(self):
        return self._min_version

    @min_version.setter
    def min_version(self, value):
        if value > self._min_version:
            self._min_version = value

    def report(self, path):
        print(f'{path}: requires {format_version(self.min_version)}')


def detect_version(path: str) -> None:
    """ Detect minimum required version of a script. """
    with open(path, 'r') as source:
        tree = ast.parse(source.read())

    analyzer = Analyzer()
    analyzer.visit(tree)
    analyzer.report(path)


def dump_ast(path: str) -> None:
    """ Display full syntax tree. """
    with open(path, 'r') as source:
        print(ast.dump(ast.parse(source.read()), indent=4))


def format_version(version: tuple) -> str:
    """ Format version tuple into human readable string. """
    major, minor, micro = version
    if micro:
        return f'Python {major}.{minor}.{micro}'
    else:
        return f'Python {major}.{minor}'


def print_requirement(feature, version):
    print(f'{feature} requires {format_version(version)}')


def _find_pyfiles(path: str) -> list[str]:
    python_files = []
    for root, _, files in os.walk(path):
        for filename in files:
            if filename.endswith('.py'):
                python_files.append(os.path.join(root, filename))
    return python_files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='file or directory to scan')
    parser.add_argument('-d', '--dump', help='dump ast to stdout', action='store_true')
    args = parser.parse_args()

    try:
        if args.dump:
            dump_ast(args.path)
        else:
            if os.path.isfile(args.path):
                detect_version(args.path)
            elif os.path.isdir(args.path):
                files = _find_pyfiles(args.path)
                if not files:
                    print(f'Error: Found 0 python files in the directory {args.path}', file=sys.stderr)
                else:
                    for filename in files:
                        detect_version(filename)
            else:
                parser.error(f'Invalid path {args.path!r}')
    except OSError as e:
        print(f'Error reading {e.filename} ({e.strerror})', file=sys.stderr)


if __name__ == '__main__':
    main()
