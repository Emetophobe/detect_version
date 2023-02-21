#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import ast
import argparse

from pathlib import Path
from src.analyzer import Analyzer, dump_node


def detect_version(path: str | Path,
                   show_notes: bool = False,
                   quiet: bool = False
                   ) -> None:
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
                analyzer.report_version()
            else:
                analyzer.report(show_notes)
    except SyntaxError:
        raise ValueError(f'Error parsing {path}. Not a valid '
                         f'Python3 script.') from None


def detect_directory(path: str | Path,
                     show_notes: bool = False,
                     quiet: bool = False
                     ) -> None:
    """ Detect requirements of all python scripts in a directory.

    Args:
        path (str | Path): directory path.
        dump_ast (bool, optional): print ast to stdout. Defaults to False.

    Raises:
        ValueError: if the path is invalid.
    """
    path = Path(path)

    if not path.is_dir():
        raise ValueError('Invalid directory path.')

    # Get all python files (excluding dotfiles)
    script_files = list(path.rglob('[!.]*.py'))

    if not script_files:
        raise ValueError('No python scripts found.')

    for script in script_files:
        detect_version(script, show_notes, quiet)


def dump_file(path: str | Path) -> None:
    """ Print script ast to stdout.

    Args:
        path (str | Path): file path of the script.
    """
    try:
        with open(path, 'r') as source:
            dump_node(ast.parse(source.read()))
    except SyntaxError:
        raise ValueError(f'Error parsing {path}. Not a valid '
                         f'Python3 script.') from None


def main():
    parser = argparse.ArgumentParser(
        description='Detect Python script requirements using abstract syntax trees.')

    parser.add_argument(
        'path',
        help='python script or a directory of scripts',
        type=Path)

    parser.add_argument(
        '-n', '--notes',
        help='show extra requirement notes (default: False)',
        action='store_true')

    # TODO: add argument for min/max/target version

    parser.add_argument(
        '-q', '--quiet',
        help='only show minimum version requirements',
        action='store_true')

    parser.add_argument(
        '-d', '--dump',
        help='print all ast nodes to stdout (only works with a single file)',
        action='store_true')

    args = parser.parse_args()

    if args.dump and args.path.is_dir():
        parser.error('Cannot use --dump with a directory.')

    try:
        # TODO: redesign this mess
        if args.path.is_file():
            if args.dump:
                dump_file(args.path)
            else:
                detect_version(args.path, args.notes, args.quiet)
        elif args.path.is_dir():
            detect_directory(args.path, args.notes, args.quiet)
        else:
            parser.error('Invalid path. Not a file or directory.')
    except OSError as e:
        raise SystemExit(f'Error reading {e.filename} ({e.strerror})')
    except ValueError as e:
        raise SystemExit(e)


if __name__ == '__main__':
    main()
