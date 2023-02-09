#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham


import sys
import json

from os import PathLike
from pathlib import Path
from detect_version import load_json


# Directory with individual module files
MODULE_PATH = "modules"


def get_files(path: PathLike):
    """ Retrieve list of json files from modules directory. """
    path = Path(MODULE_PATH)
    if not path.is_dir():
        raise ValueError('Missing module directory')

    files = list(path.glob('*.json'))
    if not files:
        raise ValueError('Missing module files')

    return files


def combine_modules(destfile: PathLike) -> None:
    """ Merge seperate json files into a single file. """

    try:
        files = get_files(MODULE_PATH)
    except ValueError as error:
        print(error, file=sys.stderr)
        return

    merged_dict = {f.stem: load_json(f) for f in files}

    with open(destfile, 'w', encoding='utf-8') as outfile:
        json.dump(merged_dict, outfile, indent=4)

    print(f'Merged {len(files)} json files into {destfile}')


if __name__ == '__main__':
    combine_modules('modules.json')
