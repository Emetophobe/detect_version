#!/usr/bin/env python
# Copyright (c) 2019-2023  Mike Cunningham

import ast
import argparse
import sys


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
PYTHON312 = (3, 12, 0)


""" TODO list:

    0. RecursionError added (Python 3.5)
    1. Check type annotations (Python 3.6 - PEP 526)
    2. Underscores in numeric literals (Python 3.6 - PEP 515)
    3. Asynchronous Generators (Python 3.6 - PEP 525)
    4. ModuleNotFoundError exception (Python 3.6)
    5. breakpoint() function (Python 3.7)
    6. positional only arguments (Python 3.8 - PEP 570)
    7. f-strings support for self-documenting expressions; i.e f"{var=}" (Python 3.8)
    8. type hinting generics in standard collections (Python 3.9 - PEP 585)
    9. structural pattern matching aka match statement (Python 3.10 - PEP 634)
    10. new built-in async functions 'aiter', and 'anext' (Python 3.10)
    11. ExceptionGroup added (Python 3.11 - PEP 654)
    12. Exceptions can be enriched with notes (Python 3.11 - PEP 678)
"""


# Module additions across every Python 3 version
MODULE_CHANGES = {
    # Python 3.1
    PYTHON31: {
        'collection': ['OrderedDict', 'counter'],
        'importlib': []
    },

    # Python 3.2
    PYTHON32: {
        'abc': ['abstractclassmethod', 'abstractstaticmethod'],
        'argparse': [],
        'concurrent': ['futures'],
        'contextlib': ['ContextDecorator'],
        'datetime': ['timezone'],
        'dis': ['DELETE_DEREF', 'code_info', 'show_code'],
        'functools': ['lru_cache'],
        'gzip': ['compress', 'decompress'],
        'hashlib': ['algorithms_available', 'algorithms_guaranteed'],
        'html': ['escape'],
        'itertools': ['accumulate'],
        'math': ['isfinite', 'expm1', 'erf', 'erfc', 'gamma', 'lgamma'],
        'os': ['environb', 'fsencode', 'fsdecode', 'getenvb', 'get_exec_path',
               'supports_bytes_environ'],
        'reprlib': ['recursive_repr'],
        'shutil': ['make_archive', 'unpack_archive'],
        'socket': ['SOCK_CLOEXEC', 'SOCK_NONBLOCK', 'detach'],
        'ssl': ['SSLContext', 'match_hostname', 'OPENSSL_VERSION', 'OPENSSL_VERSION_INFO',
                'OPENSSL_VERSION_NUMBER'],
        'sys': ['hash_info'],
        'sysconfig': [],
        'threading': ['Barrier'],
    },

    # Python 3.3
    PYTHON33: {
        'collections.abc': ['abc', 'ChainMap'],
        'crypt': ['METHOD_SHA256', 'METHOD_SHA512', 'METHOD_MD5', 'METHOD_CRYPT',
                  'methods', 'mksalt'],
        'faulthandler': [],
        'ipaddress': [],
        'inspect': ['signature', 'Signature', 'Parameter', 'BoundArguments'],
        'lzma': [],
        'math': ['log2'],
        'os': ['SF_NODISKIO', 'SF_MNOWAIT', 'SF_SYNC', 'XATTR_SIZE_MAX', 'XATTR_CREATE',
               'XATTR_REPLACE', 'readv', 'writev' 'pread', 'pwrite', 'sendfile',
               'getxattr', 'listxattr', 'removexattr', 'setxattr'],
        'select': ['devpoll'],
        'signal': ['pthread_kill'],
        'socket': ['CMSG_LEN', 'CMSG_SPACE', 'fromshare', 'if_nameindex', 'if_nametoindex',
                   'if_indextoname', 'recvmsg', 'recvmsg_into', 'sendmsg', 'sethostname',
                   'share'],
        'sys': ['_debugmallocstats', 'implementation', 'thread_info'],
        'threading': ['get_ident'],
        'time': ['CLOCK_REALTIME', 'clock_settime'],
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
        'dis': ['LOAD_CLASSDEREF', 'Bytecode', 'Instruction', 'get_instructions', 'stack_effect'],
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
        'os': ['cpu_count', 'get_inheritable', 'set_inheritable', 'get_handle_inheritable',
               'set_handle_inheritable'],
        'pathlib': [],
        'plistlib': ['FMT_BINARY', 'FMT_XML', 'load', 'loads', 'dump', 'dumps'],
        're': ['fullmatch'],
        'resource': ['prlimit'],
        'selectors': [],
        'ssl': ['create_default_context', 'get_default_verify_paths', 'enum_certificates',
                'enum_crls'],
        'socket': ['AF_LINK', 'set_inheritable', 'get_inheritable'],
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
        'collections.abc': ['AsyncIterable', 'AsyncIterator', 'Awaitable', 'Coroutine',
                            'Generator'],
        'contextlib': ['redirect_stderr'],
        'html': ['HTTPStatus'],
        'inspect': ['iscoroutine', 'isawaitable'],
        'math': ['inf', 'nan'],
        'os': ['DirEntry', 'scandir'],
        'socket': ['CAN_RAW_FD_FRAMES', 'sendfile'],
        'subprocess': ['run'],
        'traceback': ['TracebackException', 'StackSummary', 'FrameSummary', 'walk_stack',
                      'walk_tb'],
        'types': ['CoroutineType', 'coroutine'],
        'typing': [],
        'urllib.request': ['HTTPPasswordMgrWithPriorAuth'],
        'zipapp': [],
    },

    # Python 3.6
    PYTHON36: {
        'ast': ['Constant'],
        'asyncio': ['run_coroutine_threadsafe', 'loop.shutdown_asyncgens'],
        'cmath': ['tau', 'inf', 'infj', 'nan', 'nanj'],
        'collections.abc': ['AsyncGenerator', 'Collection', 'Reversible'],
        'contextlib': ['AbstractContextManager'],
        'dis': ['CALL_FUNCTION_EX', 'FORMAT_VALUE'],
        'enum': ['Flag', 'IntFlag'],
        'hashlib': ['blake2b', 'blake2s', 'sha3_224', 'sha3_256', 'sha3_384', 'sha3_512',
                    'shake_128', 'shake_256', 'scrypt'],
        'inspect': ['isasyncgenfunction', 'isasyncgen'],
        'math': ['tau'],
        'os': ['fspath', 'PathLike'],
        'random': ['choices'],
        'readline': ['set_auto_history'],
        'secrets': [],
        'socket': ['AF_ALG', 'SO_DOMAIN', 'SO_PROTOCOL', 'SO_PEERSEC', 'SO_PASSSEC',
                   'TCP_USER_TIMEOUT', 'TCP_CONGESTION', 'sendmsg_afalg'],
        'statistics': ['harmonic_mean'],
        'sys': ['_enablelegacywindowsfsencoding', 'getfilesystemencodeerrors',
                'get_asyncgen_hooks', 'set_asyncgen_hooks'],
        'tracemalloc': ['DomainFilter'],
        'typing': ['TYPE_CHECKING', 'ClassVar', 'Collection', 'ContextManager', 'NewType'],
        'winreg': ['REG_QWORD', 'REG_QWORD_LITTLE_ENDIAN'],

    },

    # Python 3.7
    PYTHON37: {
        'asyncio': ['BufferedProtocol', 'all_tasks', 'create_task', 'current_task',
                    'get_running_loop', 'run'],
        'contextlib': ['AbstractAsyncContextManager', 'AsyncExitStack', 'asynccontextmanager',
                       'nullcontext'],
        'contextvars': [],
        'crypt': ['METHOD_BLOWFISH'],
        'dataclasses': [],
        'datetime': ['datetime.fromisoformat'],
        'dis': ['LOAD_METHOD'],
        'gc': ['freeze', 'unfreeze', 'get_freeze_count'],
        'http.server': ['ThreadingHTTPServer'],
        'importlib.resources': [],
        'math': ['remainder'],
        'os': ['RWF_NOWAIT', 'RWF_HIPRI', 'RWF_DSYNC', 'RWF_SYNC', 'preadv', 'pwritev',
               'register_at_fork'],
        'queue': ['SimpleQueue'],
        'socket': ['AF_VSOCK', 'CAN_ISOTP', 'TCP_NOTSENT_LOWAT', 'close', 'getblocking'],
        'sys': ['breakpointhook', 'getandroidapilevel', 'get_coroutine_origin_tracking_depth',
                'set_coroutine_origin_tracking_depth'],
        'time': ['CLOCK_BOOTTIME', 'CLOCK_PROF', 'CLOCK_UPTIM', 'clock_gettime_ns',
                 'clock_settime_ns', 'monotonic_ns', 'perf_counter_ns', 'process_time_ns',
                 'time_ns', 'thread_time', 'thread_time_ns', 'pthread_getcpuclockid'],
        'unittest.mock': ['seal'],
        'uuid': ['UUID.is_safe'],
    },

    # Python 3.8
    PYTHON38: {
        'ast': ['PyCF_ALLOW_TOP_LEVEL_AWAIT', 'PyCF_TYPE_COMMENTS', 'get_source_segment'],
        'datetime': ['date.fromisocalendar', 'datetime.fromisocalendar'],
        'curses': ['ncurses_version'],
        'fcntl': ['F_ADD_SEALS', 'F_GET_SEALS', 'F_SEAL_GROW', 'F_SEAL_SHRINK',
                  'F_SEAL_SEAL', 'F_SEAL_WRITE'],
        'functools': ['cached_property', 'singledispatchmethod'],
        'gettext': ['pgettext', 'dpgettext', 'npgettext', 'dnpgettext'],
        'gzip': ['BadGzipFile'],
        'importlib.metadata': [],
        'math': ['dist', 'prod', 'perm', 'comb', 'isqrt'],
        'multiprocessing': ['shared_memory'],
        'os': ['add_dll_directory', 'memfd_create'],
        'plistlib': ['UID'],
        'pprint': ['pp'],
        'shlex': ['join'],
        'socket': ['AF_QIPCRTR', 'create_server', 'has_dualstack_ipv6'],
        'statistics': ['NormalDist', 'fmean', 'geometric_mean', 'multimode', 'quantiles'],
        'sys': ['unraisablehook'],
        'threading': ['excepthook', 'get_native_id'],
        'time': ['CLOCK_UPTIME_RAW'],
        'types': ['CellType', 'ClassMethodDescriptorType', 'MethodDescriptorType',
                  'MethodWrapperType', 'WrapperDescriptorType', 'resolve_bases',],
        'typing': ['Final', 'Literal', 'Protocol', 'SupportsIndex', 'TypedDict', 'final',
                   'get_args', 'get_origin', 'runtime_checkable'],
        'unicodedata': ['is_normalized'],
        'unittest': ['IsolatedAsyncioTestCase', 'addModuleCleanup', 'doModuleCleanups'],
        'unittest.mock': ['AsyncMock'],
    },

    # Python 3.9
    PYTHON39: {
        'ast': ['unparse'],
        'asyncio': ['PidfdChildWatcher', 'loop.shutdown_default_executor', 'to_thread'],
        'curses': ['get_escdelay', 'set_escdelay', 'get_tabsize', 'set_tabsize'],
        'fcntl': ['F_GETPATH', 'F_OFD_GETLK', 'F_OFD_SETLK', 'F_OFD_SETLKW',],
        'gc': ['is_finalized'],
        'graphlib': [],
        'importlib': ['resources.files', 'resources.as_file'],
        'math': ['lcm', 'nextafter', 'ulp'],
        'os': ['CLD_KILLED', 'CLD_STOPPED', 'pidfd_open', 'putenv', 'unsetenv',
               'waitstatus_to_exitcode'],
        'random': ['random.randbytes'],
        'signal': ['pidfd_send_signal'],
        'socket': ['CAN_RAW_JOIN_FILTERS', 'CAN_J1939', 'IPPROTO_UDPLITE',
                   'send_fds', 'recv_fds'],
        'sys': ['platlibdir'],
        'tracemalloc': ['reset_peak'],
        'typing': ['Annotated'],
        'zoneinfo': [],
    },

    # Python 3.10
    PYTHON310: {
        'base64': ['b32hexencode', 'b32hexdecode'],
        'codecs': ['unregister'],
        'contextlib': ['AsyncContextDecorator', 'aclosing'],
        'curses': ['has_extended_color_support'],
        'dis': ['MATCH_CLASS'],
        'fcntl': ['F_GETPIPE_SZ', 'F_SETPIPE_SZ'],
        'importlib.metadata': ['packages_distributions'],
        'inspect': ['get_annotations'],
        'itertools': ['pairwise'],
        'os': ['EFD_CLOEXEC', 'EFD_NONBLOCK', 'EFD_SEMAPHORE', 'O_EVTONLY', 'O_FSYNC',
               'O_SYMLINK', 'O_NOFOLLOW_ANY', 'RWF_APPEND', 'SPLICE_F_MOVE',
               'SPLICE_F_NONBLOCK', 'SPLICE_F_MORE', 'eventfd', 'eventfd_read',
               'eventfd_write', 'splice'],
        'platform': ['freedesktop_os_release'],
        'statistics': ['covariance', 'correlation', 'linear_regression'],
        'sys': ['orig_argv', 'stdlib_module_names'],
        'threading': ['__excepthook__', 'getprofile', 'gettrace'],
        'types': ['EllipsisType', 'NoneType', 'NotImplementedType', 'UnionType'],
        'typing': ['is_typeddict'],
        'xml.sax.handler': ['LexicalHandler'],
    },

    # Python 3.11
    PYTHON311: {
        'asyncio': ['Barrier', 'BrokenBarrierError', 'Runner', 'TaskGroup', 'Timeout',
                    'timeout'],
        'contextlib': ['chdir'],
        'datetime': ['datetime.UTC'],
        'dis': ['ASYNC_GEN_WRAP', 'COPY_FREE_VARS', 'CALL', 'COPY', 'KW_NAMES', 'PRECALL',
                'PUSH_NULL', 'SEND', 'SWAP', 'RESUME', 'RETURN_GENERATOR', 'Positions'],
        'enum': ['EnumType', 'ReprEnum', 'StrEnum', 'global_enum', 'member', 'nonmember',
                 'property', 'show_flag_values', 'verify'],
        'fcntl': ['F_DUP2FD', 'F_DUP2FD_CLOEXEC'],
        'hashlib': ['file_digest'],
        'inspect': ['getmembers_static', 'ismethodwrapper'],
        'locale': ['getencoding'],
        'logging': ['getLevelNamesMapping'],
        'math': ['cbrt', 'exp2'],
        'operator': ['call'],
        'os': ['SF_NOCACHE'],
        'socket': ['SCM_CREDS2', 'LOCAL_CREDS', 'LOCAL_CREDS_PERSISTENT',
                   'SO_INCOMING_CPU'],
        'sqlite3': ['Blob'],
        'sys': ['exception'],
        'string': ['get_identifiers', 'is_valid'],
        'tomllib': [],
        'typing': ['TypeVarTuple', 'Required', 'Never', 'NotRequired', 'Self', 'LiteralString',
                   'assert_never', 'assert_type', 'get_overloads', 'clear_overloads',
                   'dataclass_transform', 'reveal_type'],
        'unittest': ['enterModuleContext'],
        'wsgiref.types': [],
        'zipfile': ['ZipFile.mkdir'],
    },

    # Python 3.12 (Preliminary alpha changes)
    PYTHON312: {
        'dis': ['hasarg'],
        'inspect': ['markcoroutinefunction'],
        'math': ['sumprod'],
        'os': ['PIDFD_NONBLOCK', 'path.isjunction', 'path.splitroot'],
        'sys': ['activate_stack_trampoline', 'deactivate_stack_trampoline',
                'is_stack_trampoline_active'],
        'threading': ['settrace_all_threads', 'setprofile_all_threads'],
    }
}


class Analyzer(ast.NodeVisitor):
    def __init__(self):
        self.min_version = PYTHON3
        self.requirements = set()

    def generic_visit(self, node):
        if type(node).__name__ == 'Match':
            # Structural pattern matching was added in Python 3.10
            # Currently there is no visit_Match equivalent so this is a workaround
            self.update_requirements('match statement', PYTHON310)

        super().generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # Async function was added in Python 3.5
        self.update_requirements('async function', PYTHON35)

    def visit_AsyncFor(self, node: ast.AsyncFor):
        # Async for loop was added in Python 3.5
        self.update_requirements('async for loop', PYTHON35)

    def visit_AsyncWith(self, node: ast.AsyncWith):
        print('AsyncWith:', node.items)

    def visit_Import(self, node: ast.Import):
        """ Scan import statement for specific modules. """
        for alias in node.names:
            for version, changes in MODULE_CHANGES.items():
                for module, additions in changes.items():
                    if module == alias.name and not additions:
                        self.update_requirements(f'{module} module', version)

                    elif alias.name in additions:
                        self.update_requirements(f'{module}.{alias.name}', version)

        self.generic_visit(node)

    def visit_MatMult(self, node: ast.MatMult):
        print('visit_MatMult:', node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """ Scan from ... import ... statement for specific modules. """
        for alias in node.names:
            for version, changes in MODULE_CHANGES.items():
                for module, additions in changes.items():
                    if node.module == module and alias.name in additions:
                        self.update_requirements(f'{module}.{alias.name}', version)

        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        # Assigned expression aka walrus operator was added in Python 3.8
        if isinstance(node.test, ast.NamedExpr):
            self.update_requirements('assignment expression', PYTHON38)

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        print('ExceptHandler:', node.name, node.body)
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp):
        # print(f'visit_IfExp: {node.test=}')
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr):
        """ Scan for fstrings which were added in Python 3.6 """
        self.update_requirements('fstring', PYTHON36)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        #print('visit_Call', node.func, node.args)

        if isinstance(node.func, ast.Name):
            pass
        elif isinstance(node.func, ast.Attribute):
            #print('visit_Call attribute:', node.func.value.id, node.func.attr)
            pass

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if isinstance(node.value, ast.Name):
            self.check_attribute(node.value.id, node.attr)
        elif isinstance(node.value, ast.Attribute):
            if not hasattr(node.value, 'id'):
                if hasattr(node.value, 'value'):
                    self.check_attribute(node.value.value, node.attr)
            else:
                self.check_attribute(node.value.id, node.attr)

        self.generic_visit(node)

    def check_attribute(self, name, attr):
        for version, changes in MODULE_CHANGES.items():
            for module, additions in changes.items():
                if name == module and attr in additions:
                    self.update_requirements(f'{name}.{attr}', version)

    def visit_Expr(self, node: ast.Expr):
        #print('visit_Expr', node.value)
        self.generic_visit(node)

    def visit_Expression(self, node: ast.Expression):
        #print('visit_Expression', node.body)
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        """ Support for multiple with statements was added in Python 3.1 """
        if len(node.items) > 1:
            self.update_requirements('multiple "with" clauses', PYTHON31)
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom):
        """ Scan for "yield from" statements which were added in Python 3.3 """
        self.update_requirements('"yield from" statement', PYTHON33)
        self.generic_visit(node)

    def visit_Str(self, node: ast.Str):
        if node.kind == 'u':
            # Explicit unicode literals were added in Python 3.3
            self.update_requirements('unicode literal', PYTHON33)
        self.generic_visit(node)

    def update_requirements(self, feature, version):
        """ Update script requirements. """
        self.requirements.add(f'{feature} requires {format_version(version)}')
        self.min_version = max(self.min_version, version)

    def report(self, path):
        """ Print a final report. """
        print(f'{path}: requires {format_version(self.min_version)}')
        for requirement in self.requirements:
            print(f'  {requirement}')


def detect_version(path: str) -> None:
    """ Detect minimum version required to run script. """
    with open(path, 'r') as source:
        tree = ast.parse(source.read())

    analyzer = Analyzer()
    analyzer.visit(tree)
    analyzer.report(path)


def format_version(version: tuple) -> str:
    """ Format version tuple into human readable string. """
    major, minor, micro = version
    if micro:
        return f'Python {major}.{minor}.{micro}'
    else:
        return f'Python {major}.{minor}'


def dump_ast(path: str) -> None:
    """ Print ast to stdout. """
    with open(path, 'r') as source:
        tree = ast.parse(source.read())
        print(ast.dump(tree, indent=4))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='python file to scan')
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
