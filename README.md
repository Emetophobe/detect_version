# detect_version.py

Detect the minimum version required to run a Python script.

Can detect most API changes between Python 3.0 and Python 3.11 (with preliminary support for Python 3.12). This includes new modules, constants, functions, and exceptions. New features are also checked such as async/await in 3.5, fstrings in 3.6, and structural pattern matching in 3.10.

Things that are currently checked:

* Changes to built-in functions, exceptions, and modules between Python 3.0 and 3.11
* Multiple context managers which were added in Python 3.1
* "yield from" statements added in Python 3.3
* Unicode literals in added Python 3.3 (example: u"this is a unicode literal")
* Formatted string literals (fstrings) in Python 3.6
* Async coroutines with the asyncio module in Python 3.4 and async/await keywords in Python 3.7
* Structural pattern matching (match/case statement) in Python 3.10

Things that are not checked:

* Class methods and attribute changes. For example the `str` class added the `format_map()` method in Python 3.2 and the `case_fold()` method in Python 3.3. This would require much deeper code analysis that is not currently possible with the ast library.

Example output:

    ```
    $ python detect_version.py detect_version.py

    detect_version.py: requires 3.6
      argparse requires 3.2
      ast.Constant requires 3.6
      fstring requires Python 3.6
      os.PathLike requires 3.6
    ```

### Requirements:

    Python 3.6

### Installation:

    git clone https://github.com/Emetophobe/detect_version.git

### Usage:

    python detect_version.py <script>


## This script is currently in development. Use at your own risk. Bug reports or suggestions are welcome.
