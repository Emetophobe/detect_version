#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import ast
import argparse

from pathlib import Path
from src import Analyzer, dump_node

# Program version
__version__ = '0.6.2'


def detect_version(path: str | Path,
                   show_notes: bool = False,
                   quiet: bool = False
                   ) -> None:
    """Analyze a Python script (.py file) and print requirements.

    Args:
        path (str | Path): file path of the script.
        dump_ast (bool, optional): print ast to stdout. Defaults to False.
    """
    with open(path, 'r') as source:
        tree = ast.parse(source.read())

        analyzer = Analyzer(path)
        analyzer.visit(tree)

        if quiet:
            analyzer.report_version()
        else:
            analyzer.report(show_notes)


def dump_file(path: str | Path) -> None:
    """ Print script ast to stdout.

    Args:
        path (str | Path): file path of the script.
    """
    with open(path, 'r') as source:
        dump_node(ast.parse(source.read()))


def main():
    parser = argparse.ArgumentParser(
        description='Detect Python script requirements using abstract syntax trees.')

    parser.add_argument(
        'path',
        help='list of python files or directories',
        nargs='+')

    parser.add_argument(
        '-n', '--notes',
        help='show feature notes',
        action='store_true')

    # TODO: add argument for min/max/target version

    parser.add_argument(
        '-q', '--quiet',
        help='only show minimum version requirements',
        action='store_true')

    parser.add_argument(
        '-d', '--dump',
        help='print ast to stdout (only works with a single file)',
        action='store_true')

    args = parser.parse_args()

    # Get list of unique paths
    uniques = {}
    for path in args.path:
        path = Path(path)
        if path.is_file():
            uniques[path.resolve()] = path
        elif path.is_dir():
            for filename in path.rglob('[!.]*.py'):
                uniques[filename.resolve()] = filename
        else:
            parser.error(f'{path.name!r} is not a file or directory.')

    files = list(uniques.values())

    if not files:
        parser.error('Invalid path: No python scripts found.')

    if len(files) > 1 and args.dump:
        parser.error('Cannot use --dump with multiple files.')

    # Parse python scripts
    try:
        for filename in files:
            if args.dump:
                dump_file(filename)
            else:
                detect_version(filename, args.notes, args.quiet)
    except OSError as e:
        raise SystemExit(f'Error reading {e.filename} ({e.strerror})')
    except ValueError as e:
        raise SystemExit(e)
    except SyntaxError:
        raise SystemExit(f'Error parsing {filename}. Not a valid '
                         f'Python 3.0 script.') from None


if __name__ == '__main__':
    main()
