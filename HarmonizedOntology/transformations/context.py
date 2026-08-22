from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any, Literal, Protocol, cast

from rdflib import Graph, URIRef


class XMLTreeProtocol(Protocol):
    def findall(self, path: str, namespaces: dict[str, str]) -> list[Any]:
        ...


class ExtractionIndexProtocol(Protocol):
    def identifiers_for(
        self, prefix: Literal["std", "mpkg", "cls", "pred"]
    ) -> dict[str | None, URIRef]:
        ...


class TransformationContext:
    def __init__(
        self,
        tree: XMLTreeProtocol,
        source_iri: URIRef,
        graph: Graph | None = None,
        strategies: MutableMapping[str, Any] | None = None,
        extraction_index: ExtractionIndexProtocol | None = None,
    ) -> None:
        self.tree = tree
        self.source_iri = source_iri
        self.graph = graph if graph is not None else Graph()
        self.metadata: dict[str, Any] = {}
        self.strategies = strategies if strategies is not None else {}
        if extraction_index is None:
            from .implementations.BaseTransformation import ExtractionIndex

            extraction_index = ExtractionIndex(tree)
        self.extraction_index: ExtractionIndexProtocol = cast(
            ExtractionIndexProtocol, extraction_index
        )