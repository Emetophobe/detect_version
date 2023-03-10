# Copyright (c) 2019-2023  Mike Cunningham


from typing import Optional
from src import Version


class Requirement:
    """ A requirement holds a feature's version requirements (added, deprecated,
    and removed versions).

    Requirements have one, two, or all three version attributes:

        added:      Version when feature was added.
        deprecated: Version when feature was deprecated.
        removed:    Version when feature was removed.

    Requirements can also have extra details. These attributes aren't used by
    every requirement:

        notes:      optional notes (like PEP number).
        items:      optional extras.

    Examples:

        Requirement("3.6", None, None)      # added 3.6
        Requirement("3.6", "3.9", None)     # added 3.6, deprecated 3.9

    """

    def __init__(self,
                 name: str,
                 added: Optional[str] = None,
                 deprecated: Optional[str] = None,
                 removed: Optional[str] = None,
                 notes: Optional[str] = None,
                 items: Optional[list[str]] = None,
                 ) -> None:
        """ Initialize feature requirements.

        Args:
            name (str):
                Name of the feature or module.

            added (str, optional):
                Version when feature was added. Defaults to None.

            deprecated (str, optional):
                Version when feature was deprecated. Defaults to None.

            removed (str, optional):
                Version when feature was removed. Defaults to None.

            note (str, optional):
                Optional note or comment. Defaults to None.

            items (list[str], optional):
                Optional item list. Defaults to None.

        Raises:
            ValueError: if an argument is missing.
        """
        if not any((added, deprecated, removed)):
            raise ValueError('Require atleast one version (added, deprecated,'
                             ' or removed).')

        self.name = name
        self.added = added
        self.deprecated = deprecated
        self.removed = removed
        self.notes = notes
        self.items = items

    def versions(self) -> tuple[str, str, str]:
        """ Returns a tuple of the version requirements. """
        return (self.added, self.deprecated, self.removed)

    def __lt__(self, other: object) -> bool:
        """ Less than operator is used for sorting requirements. """
        if not isinstance(other, Requirement):
            raise TypeError(f'Expected a Requirement, received a {type(other).__name__}')

        # Zip versions from both instances and compare them one by one
        for version, other_ver in zip(self.versions(), other.versions()):
            if Version(version) < Version(other_ver):
                return True
            elif Version(version) > Version(other_ver):
                return False

        # Finally sort by name
        return self.name < other.name

    def __eq__(self, other: object) -> bool:
        """ Compare two requirements. """
        if not isinstance(other, Requirement):
            raise TypeError(f'Expected a Requirement, received a {type(other).__name__}')

        return str(self) == str(other)

    def __str__(self) -> str:
        """ Returns a string representation created from the dictionary values. """
        return f'{", ".join(str(s) for s in self.__dict__.values())}'
