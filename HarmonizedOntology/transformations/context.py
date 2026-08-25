from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any, Protocol

from rdflib import Graph, Namespace, URIRef

NS = {"UML": "omg.org/UML1.3"}
HO = Namespace("https://def.isotc211.org/def/ho/")

ISO_PREFIXES = {
    "cls": "https://def.isotc211.org/class/",
    "ho": "https://def.isotc211.org/def/ho/",
    "mpkg": "https://def.isotc211.org/package/",
    "pred": "https://def.isotc211.org/pred/",
    "std": "https://def.isotc211.org/standard/",
    "schema": "http://schema.org/",
}
SCHEMA = Namespace(ISO_PREFIXES["schema"])
EXCLUDED_CLASS_STEREOTYPES = {"dataType", "codeList", "CodeList"}


def bind_iso_prefixes(graph: Graph):
    for key, value in ISO_PREFIXES.items():
        graph.bind(key, value)


def extract_description(uml_element) -> str | None:
    descriptions = uml_element.xpath(
        "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='documentation']/@value",
        namespaces=NS,
    )
    if not descriptions:
        return None
    import html
    import re

    description = html.unescape(descriptions[0])
    description = re.sub(r"<[^>]+>", "", description)
    description = " ".join(description.split())
    return description if description else None


class XMLTreeProtocol(Protocol):
    def findall(self, path: str, namespaces: dict[str, str]) -> list[Any]:
        ...


class TransformationContext:
    def __init__(
        self,
        tree: XMLTreeProtocol,
        source_iri: URIRef,
        graph: Graph | None = None,
        strategies: MutableMapping[str, Any] | None = None,
        iri_registry=None,
    ) -> None:
        self.tree = tree
        self.source_iri = source_iri
        self.graph = graph if graph is not None else Graph()
        self.metadata: dict[str, Any] = {}
        self.strategies = strategies if strategies is not None else {}
        if iri_registry is None:
            from .identifiers import IRIService

            iri_registry = IRIService(tree)
        self.iri_registry = iri_registry
