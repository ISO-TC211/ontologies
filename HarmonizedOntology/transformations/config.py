from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping


class ConfigurationError(ValueError):
    """Raised when a transformation profile or strategy selection is invalid."""


@dataclass(frozen=True)
class TransformationConfig:
    paper: str
    strategies: Mapping[str, str] = field(default_factory=dict)
    configuration_id: str = field(init=False)

    def __post_init__(self):
        profiles = _profiles()
        if self.paper not in profiles:
            raise ConfigurationError(
                f"Unknown paper '{self.paper}'. Available papers: {sorted(profiles)}"
            )
        selected = dict(self.strategies)
        profile = profiles[self.paper]
        unknown_points = set(selected) - set(profile.baselines)
        if unknown_points:
            raise ConfigurationError(
                f"Unknown decision point(s): {sorted(unknown_points)}. "
                f"Available: {sorted(profile.baselines)}"
            )
        resolved = dict(profile.baselines)
        for point, strategy in selected.items():
            if strategy not in profile.strategies[point]:
                raise ConfigurationError(
                    f"Unknown strategy '{strategy}' for '{point}'. "
                    f"Available: {sorted(profile.strategies[point])}"
                )
            resolved[point] = strategy
        object.__setattr__(self, "strategies", MappingProxyType(resolved))
        canonical = self.paper + "|" + "|".join(
            f"{point}={resolved[point]}" for point in sorted(resolved)
        )
        object.__setattr__(self, "configuration_id", sha256(canonical.encode()).hexdigest()[:16])

    @property
    def profile(self):
        return _profiles()[self.paper]


def _profiles():
    from .profiles import PROFILES

    return PROFILES