# detect_version.py

Detect the minimum version required to run a Python script.

Can detect most API changes between Python 3.0 and Python 3.11 (with preliminary support for Python 3.12). This includes new modules, constants, functions, and exceptions. New features are also checked such as async/await in 3.5, fstrings in 3.6, and structural pattern matching in 3.10.

Uses the built-in ast module to parse Python scripts.

Things that are checked:

* Several hundred module additions between Python 3.0 and Python 3.12. This includes new modules, constants, functions, and exceptions (I probably missed a few)
* multiple context managers in Python 3.1
* unicode literals in Python 3.3
* "yield from" statements in Python 3.3
* type hinting with the typing module in Python 3.5
* async functionality with the asyncio module in Python 3.4 and async/await in Python 3.5
* structural pattern matching (match statement) in Python 3.10

Things that currently are not checked:

* Class method changes. For example the `str` class added the `format_map()` method in Python 3.2 and the `case_fold()` method in Python 3.3. There have been hundreds (or thousands?) of method changes to the built-in classes over the years, doing that type of code analysis would be non-trivial. This may change in the future if I figure it out.

* Module deprecations or removals (this may be a future feature as well)


### Requirements:

    Python 3.6

### Installation:

    git clone https://github.com/Emetophobe/detect_version.git

### Usage:

    python detect_version.py <script>


## Note: This script is currently in development. Bug reports or suggestions are welcome.
