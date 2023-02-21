# Copyright (c) 2019-2023  Mike Cunningham


from typing import Optional
from src import Version


class Requirement:
    """ A requirement holds a feature's changelog. """
    def __init__(self,
                 added: Optional[str] = None,
                 deprecated: Optional[str] = None,
                 removed: Optional[str] = None,
                 note: Optional[str] = None,
                 items: Optional[list[str]] = None,
                 ) -> None:
        """ Initialize feature requirements.

        Args:
            added (str, optional):
                Version when feature was added. Defaults to None.

            deprecated (str, optional):
                Version when feature was deprecated. Defaults to None.

            removed (str, optional):
                Version when feature was removed. Defaults to None.

            note (str, optional):
                optional note or comment. Defaults to None.

            items (list[str], optional):
                optional item list. Defaults to None.
        """
        self.added = added
        self.deprecated = deprecated
        self.removed = removed
        self.note = note
        self.items = items

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Requirement):
            raise TypeError(f'Expected a Requirement, received a {type(other).__name__}')

        # Compare the 3 version tuples (added, deprecated, removed)
        for version, other_ver in zip(self.versions(), other.versions()):
            if version < other_ver:
                return True
            elif version > other_ver:
                return False
        return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Requirement):
            return False

        return str(self) == str(other)

    def versions(self) -> tuple[Version, Version, Version]:
        """ Convert string versions to tuple versions. """
        return Version(self.added), Version(self.deprecated), Version(self.removed)

    def __str__(self) -> str:
        return f'{self.added}, {self.deprecated}, {self.removed}, {self.note}'
