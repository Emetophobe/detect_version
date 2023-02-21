# Copyright (c) 2019-2023  Mike Cunningham

import json
from collections.abc import KeysView, ItemsView
from pathlib import Path
from typing import Optional
from src import Requirement


class Changelog():
    """ A simple changelog dictionary loaded from a json file. """

    def __init__(self, filename: str | Path) -> None:
        """ Initialize changelog. """
        with open(filename, 'r') as source:
            self.changelog = json.load(source)

    def get_requirement(self, name: str) -> Optional[Requirement]:
        """ Get a feature requirement from the changelog.

        Args:
            name (str): name of the feature.

        Returns:
            Requirement: The feature requirement, or None if no requirement.
        """
        try:
            return Requirement(**self.changelog[name])
        except KeyError:
            return None

    def keys(self) -> KeysView:
        return self.changelog.keys()

    def items(self) -> ItemsView:
        return self.changelog.items()

    def __getitem__(self, feature: str) -> Optional[Requirement]:
        return self.get_requirement(feature)

    def __contains__(self, feature: str) -> bool:
        return feature in self.changelog.items()
