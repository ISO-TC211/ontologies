from __future__ import annotations

import re
from pathlib import Path
from typing import Literal as TypingLiteral
from urllib.parse import quote

from lxml import etree
from rdflib import Graph, Namespace, URIRef

from .context import ISO_PREFIXES, NS


def element_name(element: etree._Element | str, element_type: TypingLiteral["mpkg", "cls", "pred", "std"]) -> str:
    if isinstance(element, etree._Element):
        name = element.get("name", "(unnamed element)")
    else:
        name = element

    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", name)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)

    if element_type == "pred":
        name = name.lower()
    else:
        name = name.title()

    return name


def make_iri(prefix: str, elem: etree._Element | Path | str) -> URIRef:
    if isinstance(elem, etree._Element):
        name = elem.get("name")
        if name is None:
            return None
        parts = name.split(" ")
        name = parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
    elif isinstance(elem, Path):
        name = elem.name.replace(".xml", "")
        name = name.replace(" Edition 1", "")
        name = name.replace(" ", "")
    else:
        name = elem.replace(" ", "")

    return URIRef(ISO_PREFIXES[prefix] + quote(name, safe=""))


def replace_iris_in_graph(graph: Graph, replacements: list[tuple[str, str]]) -> Graph:
    iri_map = {URIRef(old): URIRef(new) for old, new in replacements}
    triples_to_remove = []
    triples_to_add = []
    for subj, pred, obj in graph:
        new_subj = iri_map.get(subj, subj)
        new_pred = iri_map.get(pred, pred)
        new_obj = iri_map.get(obj, obj)
        if (new_subj != subj) or (new_pred != pred) or (new_obj != obj):
            triples_to_remove.append((subj, pred, obj))
            triples_to_add.append((new_subj, new_pred, new_obj))
    for triple in triples_to_remove:
        graph.remove(triple)
    for triple in triples_to_add:
        graph.add(triple)
    return graph


def make_identifiers_map(tree, prefix: TypingLiteral["std", "mpkg", "cls", "pred"]):
    ids = {}
    xpaths = {"std": "", "mpkg": "Package", "cls": "Class", "pred": "Association"}

    for elem in tree.findall(f".//UML:{xpaths[prefix]}", namespaces=NS):
        ids[elem.get("xmi.id")] = make_iri(prefix, elem)

    if prefix == "pred":
        for elem in tree.findall(".//UML:Attribute", namespaces=NS):
            if elem.get("name") is not None:
                iri = make_iri(prefix, elem)
                if iri is not None:
                    ids[elem.xpath(
                        "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_guid']/@value",
                        namespaces=NS,
                    )[0].strip("{}")] = iri
    return ids


class ExtractionIndex:
    def __init__(self, tree):
        self.identifiers = {
            prefix: make_identifiers_map(tree, prefix)
            for prefix in ("mpkg", "cls", "pred")
        }

    def identifiers_for(self, prefix: TypingLiteral["std", "mpkg", "cls", "pred"]):
        return self.identifiers[prefix]
