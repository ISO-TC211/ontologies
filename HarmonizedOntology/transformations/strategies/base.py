from __future__ import annotations

from abc import ABC, abstractmethod


class RuleStrategy(ABC):
    name = ""
    source = ""

    @abstractmethod
    def apply(self, context, **kwargs):
        raise NotImplementedError

    @property
    def source_metadata(self):
        return {"source": self.source}