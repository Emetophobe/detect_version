# Copyright (c) 2019-2023  Mike Cunningham

import json
from collections.abc import KeysView, ItemsView
from pathlib import Path
from typing import Optional
from src import Requirement


class Changelog:
    """ A simple changelog dictionary read from a json file. """

    def __init__(self, path: str | Path) -> None:
        """ Initialize changelog from a json file.

        Args:
            path (str | Path): path of the json file.
        """
        with open(path, 'r') as source:
            self.changelog = json.load(source)

    def get_requirement(self, feature: str) -> Optional[Requirement]:
        """ Get a feature requirement from the changelog.

        Args:
            feature (str): name of the feature.

        Returns:
            Requirement: The feature requirement, or None if no feature found.
        """
        if changes := self.changelog.get(feature, None):
            return Requirement(**changes)
        else:
            return None

    def keys(self) -> KeysView:
        return self.changelog.keys()

    def items(self) -> ItemsView:
        return self.changelog.items()

    def __getitem__(self, name: str) -> Optional[Requirement]:
        return self.get_requirement(name)

    def __contains__(self, name: str) -> bool:
        return name in self.changelog.keys()
