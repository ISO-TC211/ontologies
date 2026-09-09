from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal as TypingLiteral
from urllib.parse import quote

from lxml import etree
from rdflib import URIRef

from .context import MODEL_PREFIX, NS


def element_name(element: etree._Element | str, element_type: TypingLiteral["mpkg", "cls", "pred", "std"]) -> str:
    if isinstance(element, etree._Element):
        name = element.get("name", "(unnamed element)")
    else:
        name = element
    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", name)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)
    return name.lower() if element_type == "pred" else name.title()


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
        chain: list[tuple[str, str]] = []
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


def _path_iri(base: str, segments: list[str]) -> URIRef:
    return URIRef(base + "/".join(quote(segment, safe="") for segment in segments))


def sanitize_prefix(document_name: str) -> str:
    """Return a Turtle-safe, readable prefix candidate for a document name."""
    prefix = re.sub(r"[^A-Za-z0-9_]", "", document_name)
    if not prefix:
        return "doc"
    if not prefix[0].isalpha():
        prefix = f"doc{prefix}"
    return prefix


def make_iri(elem: etree._Element | Path | str) -> URIRef:
    """Build a standalone IRI."""
    if isinstance(elem, etree._Element):
        name = elem.get("name")
        assert name is not None
    else:
        name = elem.name.removesuffix(".xml") if isinstance(elem, Path) else elem
    return _path_iri(MODEL_PREFIX, [name])


@dataclass(frozen=True)
class IRIRecord:
    iri: URIRef
    kind: str
    source_id: str
    package_id: str | None = None


class IRIService:
    """Central builder and resolver for generated resource IRIs."""

    def __init__(self, tree, document_name: str | None = None):
        self.tree = tree
        model = tree.find(".//UML:Model", namespaces=NS)
        if model is None or not model.get("xmi.id"):
            raise ValueError("XMI document must contain a UML:Model with an xmi.id")
        self.model_id = model.get("xmi.id")
        self.model_iri = _path_iri(
            MODEL_PREFIX, [document_name or self.model_id]
        )
        self.document_name = document_name or self.model_id
        self.document_prefix = sanitize_prefix(self.document_name)
        self.package_paths = package_paths(tree)
        self.package_iris: dict[str, URIRef] = {}
        self.class_iris: dict[str, URIRef] = {}
        self.property_iris: dict[str, URIRef] = {}
        self.class_ids_by_name: dict[str, list[str]] = {}
        self.class_package_ids: dict[str, str | None] = {}
        self.reverse: dict[URIRef, IRIRecord] = {}
        self._build_packages()
        self._build_classes()
        self._build_properties()

    def _element_iri(self, xmi_id: str) -> URIRef:
        return URIRef(f"{self.model_iri}#{quote(xmi_id, safe='')}")

    def iri_for(self, xmi_id: str) -> URIRef:
        return self._element_iri(xmi_id)

    def bind_prefixes(self, graph) -> str:
        """Bind this model's fragment namespace and return its allocated prefix."""
        namespace = f"{self.model_iri}#"
        namespaces = {str(uri): prefix for prefix, uri in graph.namespaces()}
        existing_prefix = namespaces.get(namespace)
        if existing_prefix is not None:
            self.document_prefix = str(existing_prefix)
            return self.document_prefix

        used_prefixes = {str(prefix) for prefix, _ in graph.namespaces()}
        prefix = self.document_prefix
        suffix = 2
        while prefix in used_prefixes:
            prefix = f"{self.document_prefix}_{suffix}"
            suffix += 1
        graph.bind(prefix, namespace)
        self.document_prefix = prefix
        return prefix

    def _register(self, record: IRIRecord, target: dict[str, URIRef]) -> None:
        assert record.source_id not in target, f"Duplicate {record.kind} ID: {record.source_id!r}"
        assert record.iri not in target.values(), f"Duplicate {record.kind} IRI: {record.iri!s}"
        assert record.iri not in self.reverse, f"IRI reused by {record.kind}: {record.iri!s}"
        target[record.source_id] = record.iri
        self.reverse[record.iri] = record

    def _build_packages(self) -> None:
        for package in self.tree.findall(".//UML:Package", namespaces=NS):
            package_id = package.get("xmi.id")
            if not package_id:continue
            self._register(
                IRIRecord(
                    self._element_iri(package_id),
                    "package",
                    package_id,
                ),
                self.package_iris,
            )

    def _build_classes(self) -> None:
        for element_type in ("Class", "Interface"):
            for cls in self.tree.findall(f".//UML:{element_type}", namespaces=NS):
                class_id = cls.get("xmi.id")
                if not class_id:
                    continue
                package_id = element_package_id(cls)
                class_iri = self._element_iri(class_id)
                self._register(IRIRecord(class_iri, "class", class_id, package_id), self.class_iris)
                self.class_ids_by_name.setdefault(cls.get("name", ""), []).append(class_id)
                self.class_package_ids[class_id] = package_id

    def _property_iri(self, context_iri: URIRef, name: str, source_id: str) -> URIRef:
        return self._element_iri(source_id)

    def _build_properties(self) -> None:
        for association in self.tree.findall(".//UML:Association", namespaces=NS):
            property_id = association.get("xmi.id")
            name = association.get("name")
            if not property_id or name is None: continue
            package_id = element_package_id(association)
            iri = self._property_iri(self.model_iri, name, property_id)
            self._register(IRIRecord(iri, "property", property_id, package_id), self.property_iris)

        for attribute in self.tree.findall(".//UML:Attribute", namespaces=NS):
            property_ids = attribute.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_guid']/@value",
                namespaces=NS,
            )
            name = attribute.get("name")
            owner_ids = attribute.xpath(
                "ancestor::*[self::UML:Class or self::UML:Interface][1]/@xmi.id",
                namespaces=NS,
            )
            if not property_ids or name is None or not owner_ids:
                continue
            property_id = property_ids[0].strip("{}")
            owner_id = owner_ids[0]
            owner_iri = self.class_iris.get(owner_id, self._element_iri(owner_id))
            self._register(
                IRIRecord(
                    self._property_iri(owner_iri, name, property_id),
                    "property",
                    property_id,
                    self.class_package_ids.get(owner_id),
                ),
                self.property_iris,
            )

    def class_iri_for_reference(self, reference: str, package_id: str | None = None) -> URIRef:
        """XMI or class name -> IRI"""
        if reference in self.class_iris:
            return self.class_iris[reference]
        candidates = self.class_ids_by_name.get(reference, [])
        if package_id:
            candidates = [candidate for candidate in candidates if self.class_package_ids.get(candidate) == package_id]
        if candidates:
            assert len(candidates) == 1, f"Class reference {reference!r} is ambiguous: {candidates!r}"
            return self.class_iris[candidates[0]]
        return make_iri(reference)

    def reverse_lookup(self, iri: URIRef) -> IRIRecord:
        try:
            return self.reverse[iri]
        except KeyError as exc:
            raise KeyError(f"Unknown generated IRI: {iri}") from exc

    def identifiers_for(self, prefix: TypingLiteral["std", "mpkg", "cls", "pred"]):
        return {
            "mpkg": self.package_iris,
            "cls": self.class_iris,
            "pred": self.property_iris,
        }[prefix]
