# detect_version.py

Detect the minimum version required to run a Python script.

Can detect most API changes between Python 3.0 and Python 3.11 (with preliminary support for Python 3.12). This includes things like fstrings in 3.6, structural pattern matching (match statement) in 3.10, with clauses, type hinting, exception groups, etc...

Uses the built-in ast module to parse the Python scripts.

Note: This is an early alpha version. Use at your own risk.

### Requirements:
    Python 3.11 (this may change in the future)

### Installation:

    git clone https://github.com/Emetophobe/detect_version.git

### Usage:

    python detect_version.py <script>
