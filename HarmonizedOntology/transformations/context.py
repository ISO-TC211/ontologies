from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any, Literal, Protocol, cast

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


def is_self_describing_enumeration(values):
    """Return whether enumeration members are readable words rather than codes."""
    return bool(values) and all(
        value.replace(" ", "").replace("-", "").replace("_", "").isalpha()
        for value in values
    )


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


def has_excluded_stereotype(uml_class) -> bool:
    stereotypes = uml_class.findall("UML:ModelElement.stereotype/UML:Stereotype", namespaces=NS)
    return any(stereotype.get("name") in EXCLUDED_CLASS_STEREOTYPES for stereotype in stereotypes)


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
            from .identifiers import ExtractionIndex

            extraction_index = ExtractionIndex(tree)
        self.extraction_index: ExtractionIndexProtocol = cast(
            ExtractionIndexProtocol, extraction_index
        )