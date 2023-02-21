# Copyright (c) 2019-2023  Mike Cunningham

class Version:
    """ The version class is used to represent a Python version.

    Versions are stored as strings internally i.e `"3.11.0", but
    are converted to tuples for sorting and comparison.

    """

    def __init__(self, version: str) -> None:
        """ Initialize version. """
        self.version = version

    def version_tuple(self) -> tuple[int, int, int]:
        """ Convert version string into a tuple for.

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
        if not isinstance(other, Version):
            raise TypeError(f'Unsupported type. Expected a Version,'
                            f' received a {type(other).__name__}')
        return self.version_tuple() < other.version_tuple()

    def __eq__(self, other: object):
        if not isinstance(other, Version):
            raise TypeError(f'Unsupported type. Expected a Version,'
                            f' received a {type(other).__name__}')

        return self.version == other.version

    def __str__(self) -> str:
        return self.version
