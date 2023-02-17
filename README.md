# detect_version.py - Alpha version

Detect the minimum version required to run a Python script.

Can detect most API changes between Python 3.0 and Python 3.11 (with experimental support for Python 3.12).  Changes include new, deprecated, and removed modules, constants, functions, and exceptions. New language features are also checked such as fstrings in 3.6 and structural pattern matching in 3.10.

Things that are currently checked:

* Changes to built-in functions, exceptions, and modules between Python 3.0 and Python 3.11.
* Changes to the language itself such as "yield from" expressions in 3.3, unicode literals in 3.5, and fstrings in 3.6.

Things that are not checked:

* Changes to class methods and attributes. For example the `str` class added the `format_map` method in Python 3.2. There is no easy way to test for this using the ast library (as far as I know). This may change in the future.

Example output:

    $ ./detect_version.py detect_version.py
    detect_version.py: requires 3.6
      argparse requires 3.2
      yield from expression requires 3.3
      os.PathLike requires 3.6
      fstring literal requires 3.6
      ast.Constant requires 3.6


### Requirements:

    Python 3.6

### Installation:

    git clone https://github.com/Emetophobe/detect_version.git

### Usage:

    python detect_version.py <script>


## This script is currently in development. Use at your own risk. Bug reports or suggestions are welcome.
