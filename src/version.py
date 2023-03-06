# Copyright (c) 2019-2023  Mike Cunningham

from typing import Optional


class Version:
    """ The version class is used to compare and sort Python versions.

    Versions are always stored as strings but are converted temporarily
    to tuples for comparison.

    Examples:

        >> ver = Version("3.5.3")

        >> ver
        "3.5.3"

        >> ver.as_tuple()
        (3, 5, 3)

        >> Version("3.11.0") > Version("3.2")
        True
    """

    def __init__(self, version: Optional[str]) -> None:
        """ Initialize version.

        Args:
            version (str, optional): the version string, can be None.
        """
        if not valid_version(version):
            raise ValueError('Invalid version string.')

        self.version = version

    def as_tuple(self) -> tuple:
        """ Convert version into a tuple.

        Returns:
            tuple: a version tuple.
        """
        if not self.version:
            return tuple()
        return tuple(int(s) for s in self.version.split('.'))

    def __lt__(self, other: object):
        if not isinstance(other, Version):
            raise TypeError(f'Expected a Version but got a {type(other).__name__}')
        return self.as_tuple() < other.as_tuple()

    def __eq__(self, other: object):
        if not isinstance(other, Version):
            raise TypeError(f'Expected a Version but got a {type(other).__name__}')
        return self.as_tuple() == other.as_tuple()

    def __str__(self) -> str:
        return self.version


def valid_version(version: str) -> bool:
    """ Returns True if the version string is valid. """
    # Empty string is valid (no requirement)
    if not version:
        return True

    # Convert version into a tuple of ints
    try:
        sections = tuple(int(s) for s in version.split('.'))
    except ValueError:
        return False

    # Require a two or three tuple; i.e (3, 11) or (3, 11, 0)
    if len(sections) < 2 or len(sections) > 3:
        return False

    # All numbers must be 0 or greater
    for number in sections:
        if number < 0:
            return False

    # Major version must be 3.x
    return sections[0] == 3
