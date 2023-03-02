# Copyright (c) 2019-2023  Mike Cunningham

import ast
import itertools
from pathlib import Path
from operator import itemgetter
from src import Version
from src import Changelog
from src import Requirement
from src import Constants


class Analyzer(ast.NodeVisitor):
    """ Parse abstract syntax tree and determine script requirements. """

    def __init__(self,
                 path: str | Path,
                 notes: bool = False
                 ) -> None:
        """ Initialize node analyzer.

        Args:
            path (str | Path): file path of the script.
            notes (str, optional): Show extra notes. Defaults to False.
        """
        self.filename = path
        self.notes = notes

        # Set minimum detected version. 3.0 is always the baseline
        self.detected_version = '3.0'

        self.features = Changelog('data/language.json')
        self.exceptions = Changelog('data/exceptions.json')
        self.functions = Changelog('data/functions.json')
        self.modules = Changelog('data/modules.json')

        self.imported = {}
        self.language_requirements = {}
        self.module_requirements = {}

    def report_version(self) -> None:
        """ Print detected version requirement. """
        print(f'{self.filename} requires: {self.detected_version}')

    def report(self) -> None:
        """ Print full script requirements. """
        print()
        print('File:', self.filename)
        print('Detected version:', self.detected_version)

        if not self.language_requirements and not self.module_requirements:
            print('Requirements: None')
            return

        print('Requirements:')
        print()

        column = '  {:<30} {:<14} {:<30}'

        # Print language and module requirements
        for requirements in (self.language_requirements, self.module_requirements):
            if not requirements:
                continue

            requirements = sorted(requirements.items(), key=itemgetter(1, 0))

            added = {}
            warnings = {}

            # Build dictionary of required and deprecated features
            for feature, requirement in requirements:
                if requirement.added:
                    added[feature] = requirement

                if requirement.deprecated or requirement.removed:
                    warnings[feature] = requirement

            # Print required features
            if added:
                for feature, requirement in added.items():
                    if self.notes and requirement.notes:
                        notes = requirement.notes
                    else:
                        notes = ''

                    print(column.format(feature, 'Python ' + requirement.added, notes))

            # Print deprecated and removed features
            if warnings:
                print('\nWarning: Found deprecated or removed features:\n')
                for feature, requirement in warnings.items():
                    description = []
                    if requirement.deprecated:
                        description.append(f'deprecated in {requirement.deprecated}')

                    if requirement.removed:
                        description.append(f'removed in {requirement.removed}')

                    print(f'  {feature} is {" and ".join(description)}')

    def visit_Import(self, node: ast.Import) -> None:
        """ Check import statements for changes to built-in modules.

        Example:
            `import a, b, c`

        Args:
            node (ast.Import): an import statement.
        """
        for alias in node.names:
            self._check_module(alias.name)

        super().generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """ Check "from import" statements for changes to built-in modules.

        Example:
            `from module import a, b, c`

        Args:
            node (ast.ImportFrom): an import from statement.
        """
        for alias in node.names:
            if alias.name == '*':
                # Handle wildcard "*" i.e "from module import *"
                self._check_module(node.module)
            else:
                # Store imported items and their modules
                self.imported[alias.name] = node.module

                # Check both the module and the imported item
                self._check_module(node.module)
                self._check_module(node.module + '.' + alias.name)

        super().generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """ Check attribute accesses for changes to built-in modules.

        Args:
            node (ast.Attribute): an attribute access (Load, Store, Del).
        """
        if attribute_name := self._get_attribute_name(node):
            if not attribute_name.startswith('self.'):
                self._check_module(attribute_name)

        super().generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """ Check function calls for changes to built-in functions.

        Args:
            node (ast.Call): a function call.
        """
        if isinstance(node.func, ast.Name):
            self._check_function(node.func.id)

        super().generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        """ Check raised exceptions for changes to built-in exceptions.

        Args:
            node (ast.Raise): a raise statement.
        """
        if isinstance(node.exc, ast.Name):
            self._check_exception(node.exc.id)
        elif isinstance(node.exc, ast.Call):
            self._check_exception(node.exc.func.id)

        super().generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """ Check caught exceptions for changes to built-in exceptions.

        Args:
            node (ast.ExceptHandler): a single except clause.
        """
        if isinstance(node.type, ast.Name):
            self._check_exception(node.type.id)
        elif isinstance(node.type, ast.Tuple):
            # Handle multiple exceptions grouped in a tuple
            # i.e; "except (Exception1, Exception2) as e:"
            for name in node.type.elts:
                self._check_exception(name.id)

        super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """ Check function definitions for annotations.

        This method only checks the return type for annotations
        (arguments are handled by visit_arguments).

        Args:
            node (ast.FunctionDef): a function definition.
        """
        # Check return type for annotations
        self._check_annotation(node.returns)
        super().generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """ Check for async functions which were added in Python 3.5 (PEP 492).

        This method also checks the return type for annotations
        (arguments are handled by visit_arguments).

        Args:
            node (ast.AsyncFunctionDef): an async function definition.
        """
        # Add requirement for async/await coroutines (PEP 492)
        self.add_feature_requirement(Constants.ASYNC_AND_AWAIT)

        # Also check return type for annotations
        self._check_annotation(node.returns)
        super().generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """ Check for annotated assignment statements (PEP 526).

        Example:
            `a: int = 5`

        Args:
            node (ast.AnnAssign): the annotated assignment.
        """
        # Add requirement for variable annotations
        self.add_feature_requirement(Constants.VARIABLE_ANNOTATIONS)

        # Also check the annotation type
        self._check_annotation(node.annotation)
        super().generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        """ Check for explicit unicode literals (PEP 414).

        Args:
            node (ast.Constant): a constant value or literal.
        """
        if node.kind == 'u':
            self.add_feature_requirement(Constants.UNICODE_LITERALS)
        super().generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """ Check for formatted string literals (fstrings) (PEP 498).

        Args:
            node (ast.JoinedStr): a fstring literal.
        """
        self.add_feature_requirement(Constants.FSTRING_LITERALS)
        super().generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        """ Check for assignment expressions (walrus operator) (PEP 572).

        Args:
            node (ast.NamedExpr): a named expression.
        """
        self.add_feature_requirement(Constants.WALRUS_OPERATOR)
        super().generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """ Check for match statements (PEP 622).

        Args:
            node (ast.Match): a match statement.
        """
        self.add_feature_requirement(Constants.MATCH_STATEMENT)
        super().generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """ Check for multiple context managers (Python 3.1)

        Example:
            `with open(file1, 'r') as infile, open(file2, 'w') as outfile:`

        Args:
            node (ast.With): a with block.

        """
        if len(node.items) > 1:
            self.add_feature_requirement(Constants.MULTIPLE_CONTEXT_MANAGERS)
        super().generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        """ Check for "yield from" expressions (PEP 380).

        Args:
            node (ast.YieldFrom): a yield from expression.

        """
        self.add_feature_requirement(Constants.YIELD_FROM_EXPRESSION)
        super().generic_visit(node)

    def visit_arguments(self, node: ast.arguments) -> None:
        """ Check function arguments for language changes.

        Args:
            node (ast.arguments): the function arguments.
        """
        # Add requirement for positional-only parameters (PEP 570)
        if node.posonlyargs:
            self.add_feature_requirement(Constants.POSONLY_ARGUMENTS)

        # Check all arguments for annotations
        for arg in itertools.chain(node.args, node.posonlyargs, node.kwonlyargs):
            self._check_annotation(arg.annotation)

        super().generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        """ Check for async comprehensions (PEP 530).

        Args:
            node (ast.comprehension): a single comprehension.
        """
        if node.is_async:
            self.add_feature_requirement(Constants.ASYNC_COMPREHENSIONS)
        super().generic_visit(node)

    def generic_visit(self, node: ast.AST) -> None:
        """ Generic node visitor. Handle nodes not covered by a specific visitor method.

        Args:
            node (ast.AST): AST is the base class for all nodes.
        """
        # Check for async/await which were added in Python 3.5
        if isinstance(node, (ast.AsyncFor, ast.AsyncWith, ast.Await)):
            self.add_feature_requirement(Constants.ASYNC_AND_AWAIT)

        # This is required to traverse child nodes
        super().generic_visit(node)

    def add_language_requirement(self, feature: str, requirement: Requirement) -> None:
        """ Add a language requirement.

        Args:
            feature (str): name of the feature.
            requirement (Requirement): the feature's requirement.
        """
        if not requirement:
            return

        if feature not in self.language_requirements.keys():
            self.update_version(requirement.added)
            self.language_requirements[feature] = requirement

    def add_module_requirement(self, name: str, requirement: Requirement) -> None:
        """ Add a module requirement.

        Args:
            name (str): name of the module or attribute.
            requirement (Requirement): the feature's requirement.
        """
        if not requirement:
            return

        if name not in self.module_requirements.keys():
            self.update_version(requirement.added)
            self.module_requirements[name] = requirement

    def add_feature_requirement(self, feature: str) -> None:
        """ Convenience method to add a language requirement by name.

        Args:
            feature (str): name of the feature.

        Raises:
            ValueError: if the feature name is invalid.
        """
        if requirement := self.features.get_requirement(feature):
            self.add_language_requirement(feature, requirement)
        else:
            raise ValueError(f'Could not find a requirement for {feature!r}.')

    def update_version(self, version: str) -> None:
        """ Update minimum Python version.

        Args:
            version (str): the version string.
        """
        if Version(version) > Version(self.detected_version):
            self.detected_version = version

    def _check_module(self, name: str) -> None:
        """ Check module requirements. Searches the modules changelog
        and updates module requirements if found.

        Args:
            name (str): name of the module or attribute.
        """
        if requirement := self.modules.get_requirement(name):
            self.add_module_requirement(name, requirement)

    def _check_exception(self, exception: str) -> None:
        """ Check exception requirements. Searches the exceptions changelog
        and updates language requirements if found.

        Args:
            exception (str): name of the exception.
        """
        if requirement := self.exceptions.get_requirement(exception):
            self.add_language_requirement(exception, requirement)

    def _check_function(self, function: str) -> None:
        """ Check function requirements. Searches the functions changelog
        and updates language requirements if found.

        Args:
            function (str): name of the function.
        """
        if requirement := self.functions.get_requirement(function):
            if function in ('aiter', 'anext'):
                # Special case: combine aiter and anext
                # functions into a single requirement
                function = Constants.AITER_AND_ANEXT

            self.add_language_requirement(function, requirement)

    def _check_annotation(self, node: ast.AST) -> None:
        """ Check annotations for language changes.

        Currently only testing for:

          * PEP 585: Type Hinting Generics In Standard Collections
          * PEP 604: Allow writing union types as X | Y

        Args:
            node (ast.AST): the annotation node.
        """
        # Search for annotations in all child nodes
        for name in self._find_annotations(node):
            # Check if the annotation was imported
            if name in self.imported.keys():
                name = self.imported[name] + '.' + name

            # Check for generic type hints (PEP 585)
            if name in self.features[Constants.GENERIC_TYPE_HINTS].items:
                self.add_feature_requirement(Constants.GENERIC_TYPE_HINTS)

    def _find_annotations(self, node: ast.AST) -> str:
        """ Recursively search a node for annotations.

        Args:
            node (ast.AST): the annotation node to search.

        Yields:
            str: name of the annotation.
        """
        # Annotation is usually a Name node
        if isinstance(node, ast.Name):
            yield node.id

        # Annotation can also be an Attribute; i.e typing.Union
        elif isinstance(node, ast.Attribute):
            # Get the full attribute name
            yield self._get_attribute_name(node)

        # Annotation can be a subscript; i.e list[int]
        elif isinstance(node, ast.Subscript):
            yield from self._find_annotations(node.value)
            yield from self._find_annotations(node.slice)

        # Annotation can be a binary operation; i.e str | bytes
        elif isinstance(node, ast.BinOp):
            # Add requirement for union type hints (PEP 604)
            self.add_feature_requirement(Constants.UNION_TYPE_HINTING)

            # Check left and right side annotations
            yield from self._find_annotations(node.left)
            yield from self._find_annotations(node.right)

        # Annotation can be a tuple; i.e Union[str, bytes]
        elif isinstance(node, ast.Tuple):
            for element in node.elts:
                yield self._find_annotations(element)

    def _get_attribute_name(self, node: ast.Name | ast.Attribute) -> str:
        """ Recursively search a node and get the full attribute name.

        Args:
            node (ast.Name | ast.Attribute): a Name or Attribute node.

        Returns:
            str: the full attribute name.
        """
        if isinstance(node, ast.Name):
            return str(node.id)
        elif isinstance(node, ast.Attribute):
            return str(self._get_attribute_name(node.value) + '.' + node.attr)
        else:
            return str()


def dump_node(node: ast.AST) -> None:
    """ Print a node to stdout.

    Args:
        node (ast.AST): an ast node.
    """
    if node:
        print(ast.dump(node, indent=4))
