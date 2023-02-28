# detect_version.py - Alpha version

Detect the minimum version required to run a Python script.

Can detect several hundred API changes between Python 3.0 and Python 3.11 (with experimental support for Python 3.12). Uses the built-in ast module to parse a Python script and scan it for feature changes.

Things that are currently checked:

* Changes to built-in modules, exceptions, constants, and functions. This includes roughly:

    * 1175 changes to built-in modules (additions, deprecations, and removals)
    * 21 new exception classes (RecursionError, ModuleNotFoundError, etc..)
    * 4 new functions (callable, breakpoint, aiter, anext)

* Changes to the Python language itself. Examples include:

    * Multiple context managers in Python 3.1
    * PEP 380 - Syntax for Delegating to a Subgenerator ("yield from")
    * PEP 414 - Explicit Unicode Literals (strings prefixed with a "u")
    * PEP 492 - Coroutines with async and await syntax
    * PEP 498 - Literal String Interpolation (fstrings)
    * PEP 525 - Asynchronous Generators (aiter and anext)
    * PEP 530 - Asynchronous Comprehensions
    * PEP 526 - Syntax for Variable Annotations
    * PEP 570 - Positional-Only Parameters
    * PEP 572 - Assignment Expressions (walrus operator)
    * PEP 585 - Type Hinting Generics In Standard Collections
    * PEP 604 - Allow writing union types as X | Y
    * PEP 622 - Structural Pattern Matching (match statement)

Things that are currently **not** checked:

* Changes to built-in class methods and attributes.
* Changes to function arguments (like new keyword arguments).


### Requirements:

    Python 3.10

### Installation:

    git clone https://github.com/Emetophobe/detect_version.git

### Usage:

    usage: detect_version.py [-h] [-n] [-q] [-d] path [path ...]

    Detect Python script requirements using abstract syntax trees.

    positional arguments:
    path         list of python files or directories

    options:
    -h, --help   show this help message and exit
    -n, --notes  show feature notes
    -q, --quiet  only show minimum version requirements
    -d, --dump   print ast to stdout (only works with a single file)

### Example output (work in progress):

    $ python detect_version.py detect_version.py

    Filename: detect_version.py
    Detected version: 3.10
    Requirements:

        f-string literals requires 3.6
        union type hinting requires 3.10
        argparse requires 3.2
        pathlib requires 3.4


## This script is currently in development. Bug reports or suggestions are welcome.
