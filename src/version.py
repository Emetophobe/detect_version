# Copyright (c) 2019-2023  Mike Cunningham

class Version:
    """ The version class is used to compare and sort Python versions.

    Versions are always stored as strings but are converted to tuples for
    comparison. Strings are dumb when it comes to comparing numbers so
    this is necessary.

    Example of the problem:

        # Bad.
        >> "3.11" > "3.2"
        False

        # Good.
        >> Version("3.11") > Version("3.2")
        True

    Other examples:

        >> ver = Version("3.11.0")

        >> ver
        "3.11.0"

        >> ver.as_tuple()
        (3, 11, 0)
    """

    def __init__(self, version: str) -> None:
        """ Initialize version.

        Args:
            version (str): the version string.
        """
        self.version = version

    def as_tuple(self) -> tuple[int, int, int]:
        """ Convert version to a tuple for sorting.

        Example:
            `version_tuple("3.11.1")` returns `(3, 11, 1)`

        Returns:
            tuple[int, int, int]:
                a tuple of (major, minor, micro) version numbers.
        """
        if not self.version:
            return tuple()
        return tuple(int(s) for s in self.version.split('.'))

    def __lt__(self, other: object):
        """ Less than operator for sorting versions. """
        if not isinstance(other, Version):
            raise TypeError(f'Unsupported type. Expected a Version,'
                            f' received a {type(other).__name__}')
        return self.as_tuple() < other.as_tuple()

    def __eq__(self, other: object):
        """ Equals operator for comparing versions. """
        if not isinstance(other, Version):
            raise TypeError(f'Unsupported type. Expected a Version,'
                            f' received a {type(other).__name__}')
        return self.as_tuple() == other.as_tuple()

    def __str__(self) -> str:
        """ Return a string representation of the version. """
        return self.version
