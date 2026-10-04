"""Expand sealed choices while leaving product contents and UUIDs to callers."""

from itertools import combinations, combinations_with_replacement
from typing import Any, Callable, Generic, Protocol, TypeVar


class Component(Protocol):
    chance: Any
    weight: Any

    def merge(self, other: Any) -> None: ...


T = TypeVar("T", bound=Component)


class ChoiceGroups(Generic[T]):
    """Independent groups; choose one compiled component from each group.

    The factory builds the caller's component type. Components provide chance,
    weight and merge(other); recursion happens when the factory builds a child.
    """

    def __init__(self, contents: dict, factory: Callable[[dict], T], name: str | None = None) -> None:
        self.groups: list[list[T]] = []
        choices: list[T] = []
        if "variable_mode" in contents:
            options = contents["variable_mode"]
            select = combinations_with_replacement if options.get("replacement", False) else combinations
            for selected in select(contents["variable"], options.get("count", 1)):
                component = factory({})
                for child in selected:
                    component.merge(factory(child))
                choices.append(component)
            weight = sum(component.chance for component in choices)
            if "weight" in options and options["weight"] != weight:
                raise ValueError(f"Weight incorrectly assigned for product {name}")
            for component in choices:
                component.weight = weight
        elif "variable" in contents:
            choices = [factory(child) for child in contents["variable"]]
        if choices:
            self.groups.append(choices)

    def merge(self, other: "ChoiceGroups[T]") -> None:
        """Retain each selected component's independent choice groups."""
        self.groups.extend(other.groups)

    def serialize(self, serialize_component: Callable[[T], dict]) -> list[dict]:
        """Keep recursive alternatives grouped in the published shape."""
        return [{"configs": [serialize_component(component) for component in group]} for group in self.groups]
