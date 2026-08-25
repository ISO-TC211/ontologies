from __future__ import annotations

import re
from pathlib import Path
from typing import Literal as TypingLiteral
from urllib.parse import quote

from lxml import etree
from rdflib import URIRef

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


def package_parent_id(package) -> str | None:
    parents = package.xpath(
        "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='parent']/@value",
        namespaces=NS,
    )
    return parents[0] if parents else None


def element_package_id(element) -> str | None:
    package_ids = element.xpath(
        "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='package']/@value",
        namespaces=NS,
    )
    return package_ids[0] if package_ids else None


def package_paths(tree) -> dict[str, list[str]]:
    """
    Return each package XMI ID's full root-to-package name path.
    i.e. {package_id : [root, ..., package], ... }
    """
    packages = {
        package.get("xmi.id"): package
        for package in tree.findall(".//UML:Package", namespaces=NS)
        if package.get("xmi.id")
    }
    paths: dict[str, list[str]] = {}

    def path_for(package_id: str) -> list[str]:
        if package_id in paths:
            return paths[package_id]
        chain = []
        visiting = set()
        current_id = package_id
        while current_id in packages and current_id not in paths and current_id not in visiting:
            visiting.add(current_id)
            package = packages[current_id]
            chain.append((current_id, package.get("name", "Unnamed package")))
            current_id = package_parent_id(package)

        path = list(paths.get(current_id, []))
        for current_id, name in reversed(chain):
            path.append(name)
            paths[current_id] = path.copy()
        return paths.get(package_id, [])

    for package_id in packages:
        path_for(package_id)
    return paths


def make_iri(
    prefix: str,
    elem: etree._Element | Path | str,
    package_path: list[str] | None = None,
) -> URIRef:
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

    segments = [quote(part, safe="") for part in (package_path or [])]
    segments.append(quote(name, safe=""))
    return URIRef(ISO_PREFIXES[prefix] + "/".join(segments))


def make_identifiers_map(
    tree,
    prefix: TypingLiteral["std", "mpkg", "cls", "pred"],
    package_path_index: dict[str, list[str]] | None = None,
):
    """Generate a stable xmi id -> IRI mapping"""
    ids = {}
    xpaths = {"std": "", "mpkg": "Package", "cls": "Class", "pred": "Association"}

    for elem in tree.findall(f".//UML:{xpaths[prefix]}", namespaces=NS):
        package_path = None
        if package_path_index is not None and prefix in {"mpkg", "cls"}:
            package_id = elem.get("xmi.id") if prefix == "mpkg" else element_package_id(elem)
            package_path = package_path_index.get(package_id)
            if prefix == "mpkg" and package_path:
                package_path = package_path[:-1]
        identifier = elem.get("xmi.id")
        iri = make_iri(prefix, elem, package_path)
        if prefix == "cls":
            assert identifier not in ids, f"Duplicate class XMI ID: {identifier!r}"
            assert iri not in ids.values(), f"Duplicate class IRI: {iri!s}"
        ids[identifier] = iri

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
        self.package_paths = package_paths(tree)
        self.identifiers = {
            prefix: make_identifiers_map(tree, prefix, self.package_paths)
            for prefix in ("mpkg", "cls", "pred")
        }
        self.class_ids_by_name = {}
        self.class_package_ids = {}
        for element in tree.findall(".//UML:Class", namespaces=NS):
            name = element.get("name")
            identifier = element.get("xmi.id")
            if name and identifier in self.identifiers["cls"]:
                self.class_ids_by_name.setdefault(name, []).append(identifier)
                self.class_package_ids[identifier] = element_package_id(element)

    def class_iri_for_reference(self, reference: str, package_id: str | None = None) -> URIRef:
        """Resolve a class XMI ID into its correct IRI"""
        class_identifiers = self.identifiers["cls"]
        if reference in class_identifiers: # XMI ID
            return class_identifiers[reference]
        candidates = self.class_ids_by_name.get(reference, []) 
        if package_id: # search in provided package
            candidates = [
                identifier
                for identifier in candidates
                if self.class_package_ids.get(identifier) == package_id
            ]
        if candidates:
            assert len(candidates) == 1, (f"Class reference {reference!r} is ambiguous: {candidates!r}")
            return class_identifiers[candidates[0]]
        return make_iri("cls", reference)

    def identifiers_for(self, prefix: TypingLiteral["std", "mpkg", "cls", "pred"]):
        return self.identifiers[prefix]
